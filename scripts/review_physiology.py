from traits.api import push_exception_handler
push_exception_handler(reraise_exceptions=True)

import tables
import cPickle as pickle
import numpy as np
import re
from os import path
from numpy.lib import recfunctions

from pyface.api import FileDialog, OK, error, ProgressDialog, information, \
        confirm, YES
from enable.api import Component, ComponentEditor
from chaco.api import LinearMapper, DataRange1D, OverlayPlotContainer
                       
from traitsui.api import VGroup, Item, View, HSplit, Tabbed, Controller
from traits.api import Instance, HasTraits, Float, DelegatesTo, CBool, Int, \
        Any, Event, Property, List, cached_property, Str, Enum, File, Range

# Used for displaying the checkboxes for channel/plot visibility config
from traitsui.api import TableEditor, ObjectColumn, EnumEditor
from traitsui.extras.checkbox_column import CheckboxColumn
from traitsui.menu import MenuBar, Menu, ActionGroup, Action

# Used for the trial log display
from traitsui.api import TabularEditor
from traitsui.tabular_adapter import TabularAdapter

from cns import get_config
from cns.channel import ProcessedFileMultiChannel, FileChannel, \
        FileMultiChannel, FileEpoch, FileTimeseries

from cns.chaco_exts.helpers import add_default_grids, add_time_axis
from cns.chaco_exts.channel_data_range import ChannelDataRange
from cns.chaco_exts.extremes_multi_channel_plot import ExtremesMultiChannelPlot
from cns.chaco_exts.multi_channel_plot import MultiChannelPlot
from cns.chaco_exts.ttl_plot import TTLPlot
from cns.chaco_exts.epoch_plot import EpochPlot
from cns.chaco_exts.timeseries_plot import TimeseriesPlot
from cns.chaco_exts.channel_range_tool import MultiChannelRangeTool
from cns.chaco_exts.channel_number_overlay import ChannelNumberOverlay
from cns.chaco_exts.threshold_overlay import ThresholdOverlay
from cns.chaco_exts.extracted_spike_overlay import ExtractedSpikeOverlay

from cns.analysis import (extract_spikes, median_std, decimate_waveform,
    truncate_waveform, zero_waveform, running_rms)

COLORS = get_config('EXPERIMENT_COLORS')
RAW_WILDCARD = get_config('PHYSIOLOGY_RAW_WILDCARD')

is_none = lambda x: x is None

fill_alpha = 0.25
line_alpha = 0.55
line_width = 0.5

CHANNEL_FORMAT = {
    'spout_TTL':    {
        'fill_color':       (0.25, 0.41, 0.88, fill_alpha), 
        'line_color':       (0.25, 0.41, 0.88, line_alpha), 
        'line_width':       line_width,
        'rect_center':      0.25, 
        'rect_height':      0.2,
    },
    'signal_TTL':   {
        'fill_color':       (0, 0, 0, fill_alpha), 
        'line_color':       (0, 0, 0, line_alpha),
        'line_width':       line_width, 
        'rect_height':      0.3, 
        'rect_center':      0.5,
    },
    'poke_TTL':     {
        'fill_color':       (.17, .54, .34, fill_alpha), 
        'line_color':       (.17, .54, .34, line_alpha), 
        'rect_center':      0.75,
        'line_width':       line_width, 
        'rect_height':      0.2,
    },
    'reaction_TTL': {
        'fill_color':       (1, 0, 0, fill_alpha), 
        'line_color':       (1, 0, 0, line_alpha),
        'line_width':       line_width, 
        'rect_height':      0.1, 
        'rect_center':      0.6,
    },
    'response_TTL': {
        'fill_color':       (0, 1, 0, fill_alpha), 
        'line_color':       (0, 1, 0, line_alpha),
        'line_width':       line_width, 
        'rect_height':      0.1, 
        'rect_center':      0.5,
    },
    'reward_TTL': {
        'fill_color':       (0, 0, 1, fill_alpha), 
        'line_color':       (0, 0, 1, line_alpha),
        'line_width':       line_width, 
        'rect_height':      0.1, 
        'rect_center':      0.4,
    },
    'TO_TTL':   {
        'fill_color':       (1, 0, 0, fill_alpha), 
        'line_color':       (1, 0, 0, line_alpha),
        'line_width':       line_width, 
        'rect_height':      0.1, 
        'rect_center':      0.1,
    },
    'response_ts':  {
        'marker':           'diamond',
        'marker_color':     (0, 1, 0, fill_alpha),
        'marker_height':    0.45,
    },
    'all_poke_epoch':  {
        'marker':           'diamond',
        'marker_color':     (0.34, 0.54, 1.0, fill_alpha),
        'marker_height':    0.8,
    },
    'poke_epoch':  {
        'marker':           'diamond',
        'marker_color':     (0.17, 0.54, 0.34, fill_alpha),
        'marker_height':    0.7,
    },
    'signal_epoch':  {
        'marker':           'diamond',
        'marker_color':     (0.5, 0.5, 0.5, fill_alpha),
        'marker_height':    0.6,
    },
    'trial_epoch':  {
        'marker':           'diamond',
        'marker_color':     (0.75, 0.25, 0.75, fill_alpha),
        'marker_height':    0.5,
    },
}

class TrialLogAdapter(TabularAdapter):
    '''
    This is a wrapper around the actual trial_log table in the HDF5 file.  Come
    to think of it, we could implement something reasonably similar for the
    on-line experiment code.
    '''

    # List of tuples (column_name, field )
    columns = [ ('#',       'trial'),
                ('P',       'parameter'),
                ('S',       'speaker'),
                ('Time',    'time'),
                ('WD',      'reaction'),
                ('RS',      'response'), 
                ]

    parameter_width = Float(75)
    reaction_width = Float(25)
    response_width = Float(25)
    speaker_width = Float(25)
    time_width = Float(65)

    response_image = Property
    reaction_image = Property
    response_text = Str(' ')
    reaction_text = Str(' ')

    parameter_text = Property
    speaker_text = Property
    time_text = Property
    trial_text = Property

    parameters = List(Str)

    def _get_parameter_text(self):
        return ', '.join('{}'.format(self.item[p]) for p in self.parameters)

    def _get_speaker_text(self):
        return self.item['speaker'][0].upper()

    def _get_time_text(self):
        seconds = self.item['start']
        return "{0}:{1:02}".format(*divmod(int(seconds), 60))

    def _get_bg_color(self):
        if self.item['valid']:
            return COLORS[self.item['ttype']]
        else:
            return '#AAAAAA'

    def _get_reaction_image(self):
        if self.item['reaction'] == 'early':
            return '@icons:array_node'
        elif self.item['reaction'] == 'normal':
            return '@icons:tuple_node'
        else:
            return '@icons:none_node'

    def _get_response_image(self):
        # Note that these are references to some icons included in ETS
        # (Enthought Tool Suite).  The icons can be found in
        # enthought/traits/ui/image/library/icons.zip under site-packages.  I
        # hand-picked a few that seemed to work for our purposes (mainly based
        # on the colors).  I wanted a spout response to have a green icon
        # associated with it (so that green on green means HIT, red on green
        # means MISS), etc.
        if self.item['response'] == 'spout':
            return '@icons:tuple_node'  # a green icon
        elif self.item['response'] == 'poke':
            return '@icons:dict_node'   # a red icon
        else:
            return '@icons:none_node'   # a gray icon

    def _get_trial_text(self):
        return str(self.row+1)

    def delete(self, object, trait, row):
        # The delete method is mapped to the delete key on the keyboard.
        # Instead of actually deleting the trial, we mark it as bad.
        obj = getattr(object, trait)

        # Flip the flag.  0 = invalid, 1 = valid.
        obj.cols.valid[row] = not obj.cols.valid[row]

trial_log_editor = TabularEditor(editable=False, 
                                 adapter=TrialLogAdapter(),
                                 selected='trial_selected')

class ChannelSetting(HasTraits): 
    # Channel number (used for indexing purposes so this should be zero-based)
    index           = Int
    # Channel number (used for GUI purposes so this should be one-based)
    gui_index       = Property(depends_on='index')
    # Should the channel be plotted?
    visible         = CBool(True)
    # Is the channel bad?
    bad             = CBool(False)
    # Should this be included in the extracted data?
    extract         = CBool(False)
    # Noise floor (computed using the algorighm recommended by the spike sorting
    # article on scholarpedia)
    std             = Float(np.nan)
    # Standard deviations above the noise floor for candidate features
    th_std          = Float(-5.0)
    # Standard deviations above the noise floor to reject candidate.  Since this
    # is a +/- reject, we should just ensure that it can never be set to a
    # negative value by using Range.
    artifact_std    = Range(0.0, np.inf, 20.0)
    # Convert to mV for displaying on-screen
    std_mv          = Property(Float, depends_on='std')
    # Thresholds to use for spike extraction (can be NaN or Inf)
    threshold       = Property(Float, depends_on='std, th_std')
    # Threshold to use for artifact reject (based on deviation above noise floor)
    artifact_threshold = Property(Float, depends_on='std, artifact_std')
    # Channel type
    classification = Enum('None', 'single-unit', 'multi-unit', 'artifact',
                          'hash', 'gross discharge')

    # We need to use a CBool datatype for the traits below because when loading
    # from the HDF5 file, PyTables returns a numpy.bool_ datatype which is not
    # recognized by the Bool trait as a valid boolean type.

    # Does the channel have an auditory response?
    auditory_response = CBool(False)
    # Does the channel have a behavior response?
    behavior_response = CBool(False)

    @cached_property
    def _get_gui_index(self):
        return self.index + 1

    @cached_property
    def _get_std_mv(self):
        return 10e3*self.std

    @cached_property
    def _get_threshold(self):
        return self.th_std*self.std

    @cached_property
    def _get_artifact_threshold(self):
        return self.artifact_std*self.std

channel_editor = TableEditor(
    columns=[ 
        ObjectColumn(name='gui_index', width=5, label='#', editable=False),
        CheckboxColumn(name='visible', width=5, label='V'), 
        CheckboxColumn(name='bad', width=5, label='B'),
        CheckboxColumn(name='extract', width=5, label='E'),
        ObjectColumn(name='th_std', width=5, label='T'),
        # The default "style" for the edit widget of a range trait uses a
        # slider.  However, this is difficult to use when imbedded in the table
        # editor.  Let's force it to be a simple field (text-entry).
        ObjectColumn(name='artifact_std', width=5, label='A', style='text'),
        ObjectColumn(name='std_mv', width=25, label=u'\u03C3 (mV)',
                     format='%.3f', editable=False),
        ObjectColumn(name='classification', width=50, label='Classification'),
        CheckboxColumn(name='auditory_response', width=5, label='AR'),
        CheckboxColumn(name='behavior_response', width=5, label='BR'),
        ],
    dclick='channel_dclicked',
    )

class PlotSetting(HasTraits):

    plot    = Instance(Component)
    visible = DelegatesTo('plot')
    name    = Str

plot_editor = TableEditor(
    columns=[
        ObjectColumn(name='name', width=75, label='Plot', editable=False),
        CheckboxColumn(name='visible', width=10, label='V'), 
        ]
    )

class PhysiologyReviewController(Controller):

    def _do_zoom(self, level, info):
        info.object.index_range.span = level

    def set_zoom_1(self, info):
        self._do_zoom(1, info)

    def set_zoom_2(self, info):
        self._do_zoom(2, info)

    def set_zoom_4(self, info):
        self._do_zoom(4, info)

    def set_zoom_8(self, info):
        self._do_zoom(8, info)

    def set_zoom_16(self, info):
        self._do_zoom(16, info)

    def open_file(self, info):
        # Get the output filename from the user
        dialog = FileDialog(action="open", wildcard=RAW_WILDCARD)
        dialog.open()
        if dialog.return_code != OK:
            return
        nodepath = get_experiment_node_dialog(dialog.path)
        if nodepath == '':
            return

        fh = tables.openFile(dialog.path, 'a', rootUEP=nodepath)
        if info.object.data_node and info.object.data_file.isopen:
            info.object.data_file.close()

        # Save the information back to the object
        info.object.data_file = fh
        info.object.data_node = fh.root
        info.object.data_filename = dialog.path
        info.object.data_pathname = nodepath
        self._update_title(info)
        self.load_settings(info)

    def _update_title(self, info):
        if info.object.batchfile:
            template = '{} >> {} - Physiology Review'
            info.ui.title = template.format(info.object.data_filename,
                                            info.object.batchfile)
        else:
            template = '{} - Physiology Review'
            info.ui.title = template.format(info.object.data_filename)
    
    def open_batchfile(self, info):
        dialog = FileDialog(action="open", 
                            wildcard='Batch file (*.bat)|*.bat|')
        dialog.open()
        if dialog.return_code != OK:
            return
        # Save the full path to the batchfile.  Don't open it (we'll open it
        # each time we need to add to it).
        info.object.batchfile = dialog.path
        self._update_title(info)

    def create_batchfile(self, info):
        dialog = FileDialog(action="save as", 
                            wildcard='Batch file (*.bat)|*.bat|')
        dialog.open()
        if dialog.return_code != OK:
            return
        if not dialog.path.endswith('bat'):
            dialog.path += '.bat'
        # Save the full path to the batchfile.  Don't open it (we'll open it
        # each time we need to add to it).
        info.object.batchfile = dialog.path
        self._update_title(info)

    def save_settings(self, info):
        settings = info.object.channel_settings
        node = info.object.data_node.data.physiology

        # If the channel_metadata table already exists, remove it.
        try:
            node.channel_metadata._f_remove()
        except tables.NoSuchNodeError:
            pass

        # Save the list of ChannelSetting objects to a table in the HDF5 file.
        # First, we create a Numpy record array (essentially a 2D array with
        # named columns) that will be passed to the createTable function.
        records = []
        for setting in settings:
            records.append(setting.trait_get().values())
        records = np.rec.fromrecords(records, names=setting.trait_get().keys())
        table = info.object.data_file.createTable(node, 'channel_metadata',
                                                  records)

        # Save the filtering/referencing settings as attributes in the table
        # node.  This code basically pulls out all of the traits on the
        # PhysiologyReview that do not have the transient metadata set to True.
        # Note that some Traits (e.g. Property, Event, etc.) already have
        # transient set to True, so I do not define them here.
        for k, v in info.object.trait_get(setting=True).items():
            table._v_attrs[k] = v
        information(info.ui.control, "Saved settings to file")

    def _load_settings(self, info, table_node):
        # This returns a Numpy record array
        records = table_node.read()

        # First, get a list of the traits in the ChannelSetting object that
        # we need to set.  Some of the traits cannot be set directly (e.g.
        # the "Property" traits such as artifact_threshold are dynamically
        # computed since they are derived from other traits in the class),
        # so we need to ensure we only pull out the "editable" traits from
        # the channel_metadata table.  Furthermore, I may have added new
        # columns in future revisions of the program that are not present in
        # the saved channel_metadat atable.  To ensure
        # backward-compatibility, we only load the columns that are present
        # in table.cols.
        traits = ChannelSetting.class_trait_names(transient=is_none)
        traits = list(np.intersect1d(traits, table_node.colnames))

        # Pull out the columns from the record array 
        records = records[traits]

        # Now, create a list of channelsetting objects!
        settings = []
        for record in records:
            kwargs = dict(zip(traits, record))
            setting = ChannelSetting(**kwargs)
            settings.append(setting)
        info.object.channel_settings = settings

        # Now, load the remaining settings!
        for k in info.object.trait_get(setting=True):
            setattr(info.object, k, table_node._v_attrs[k])

    def load_settings(self, info):
        try:
            table = info.object.data_node.data.physiology.channel_metadata
            self._load_settings(info, table)
        except (AttributeError):
            # The errors mean that we haven't saved settings information to this
            # node yet.  Revert all settings back to default (silently).
            self.default_settings(info)
        except (KeyError):
            information("Unable to load saved settings")
            self.default_settings(info)

    def copy_settings(self, info):
        dialog = FileDialog(action="open", 
                            wildcard='HDF5 file (*.hd5)|*.hd5|')
        dialog.open()
        if dialog.return_code != OK:
            return
        nodepath = get_experiment_node_dialog(dialog.path)
        if nodepath == '':
            return

        try:
            fh = tables.openFile(dialog.path, 'r', rootUEP=nodepath)
            table = fh.root.data.physiology.channel_metadata
            self._load_settings(info, table)
        except:
            information("Unable to copy settings")

    def default_settings(self, info):
        reset = ['freq_lp', 'freq_hp', 'filter_order', 'diff_mode']
        info.object.channel.reset_traits(reset)
        settings = info.object._channel_settings_default()
        info.object.channel_settings = settings

    def compute_std(self, info):
        duration = get_config('NOISE_DURATION')
        lb = info.object.index_range.low
        ub = lb + duration
        lb, ub = info.object.channel.to_samples((lb, ub))
        stdevs = median_std(info.object.channel[:,lb:ub])
        for std, setting in zip(stdevs, info.object.channel_settings):
            setting.std = std
        information(info.ui.control, "Computed standard deviation of signal")
        info.object.std_lb = lb
        info.object.std_ub = ub

    def truncate_waveform(self, info):
        result = confirm(info.ui.control, "This action will permanently alter"
                         "the data in the file and cannot be undone.  Are "
                         "you sure you wish to continue?", 
                         title="Truncate waveform")
        if result != YES:
            return

        result = confirm(info.ui.control, "Are you really sure?",
                         title="Truncate waveform")
        if result != YES:
            return

        # Truncate the waveform
        truncate_waveform(info.object.data_node, info.object.index_range.high)

        information(info.ui.control, "Truncated waveform.  Be sure to run "
                    "ptrepack or h5repack to regain the unused disk space.")

    def zero_waveform(self, info):
        result = confirm(info.ui.control, "This action will permanently alter"
                         "the data in the file and cannot be undone.  Are "
                         "you sure you wish to continue?", 
                         title="Zero waveform")
        if result != YES:
            return

        result = confirm(info.ui.control, "Are you really sure?", 
                         title="Zero waveform")
        if result != YES:
            return

        # Zero the waveform
        zero_waveform(info.object.data_node, info.object.index_range.low)

        information(info.ui.control, "Zeroed waveform.  Be sure to run "
                    "ptrepack or h5repack to recompress the file.")

    def _prepare_processing_settings(self, info):
        # Compile our referencing and filtering instructions
        processing = {}
        processing['filter_freq_lp'] = info.object.filter_freq_lp
        processing['filter_freq_hp'] = info.object.filter_freq_hp
        processing['filter_order'] = info.object.filter_order
        processing['filter_btype'] = info.object.filter_btype
        processing['bad_channels'] = info.object.bad_channels
        processing['diff_mode'] = info.object.diff_mode
        return processing

    def _prepare_extract_settings(self, info):
        settings = [s for s in info.object.channel_settings if s.extract]
        # The return statement forces an exit from this function, meaning
        # downstream code will not get executed. 

        # If settings is an empty list (i.e. no channels were selected for
        # extraction), it will evaluate to False.
        if not settings:
            error(info.ui.control, 
                  'Must specify at least one channel to extract',
                  title='No channels selected')
            return

        kwargs = {}

        processing = self._prepare_processing_settings(info)

        # Gather the arguments required by the spike extraction routine
        kwargs['processing'] = processing
        kwargs['noise_std'] = [s.std for s in settings]
        kwargs['channels'] = [s.index for s in settings]
        kwargs['threshold_stds'] = [s.th_std for s in settings]
        kwargs['rej_threshold_stds'] = [s.artifact_std for s in settings]
        kwargs['window_size'] = 2.1
        kwargs['cross_time'] = 0.5  
        kwargs['cov_samples'] = 5e3 

        return kwargs

    def compute_rms(self, info):
        filename = get_save_filename(info.object.data_filename, 'rms')
        if filename is None:
            return

        with tables.openFile(filename, 'w') as fh_out:
            output_node = fh_out.root
            input_node = info.object.data_node
            processing = self._prepare_processing_settings(info)

            # Create a progress dialog that keeps the user up-to-date on what's
            # going on since this is a fairly lengthy process.
            dialog = ProgressDialog(title='Exporting data', 
                                    min=0,
                                    can_cancel=True,
                                    max=int(info.object.channel.shape[-1]),
                                    message='Initializing ...')

            # Define a function that, when called, updates the dialog ... 
            dialog.open()

            def callback(samples, max_samples, mesg):
                if samples == max_samples:
                    dialog.close()
                dialog.change_message(mesg)
                cont, skip = dialog.update(samples)
                return not cont

            running_rms(input_node, output_node, 1, 1, processing=processing,
                        progress_callback=callback, algorithm='median')


    def extract_spikes(self, info):
        # Compile the necessary arguments to pass along to extract_spikes.  If
        # the helper method returns None, this means that there was a problem
        # with compiling the arguments (e.g. no channels were selected), so
        # return from the method.
        kwargs = self._prepare_extract_settings(info)
        if kwargs is None:
            return

        filename = get_save_filename(info.object.data_filename, 'extracted')
        if filename is None:
            return

        with tables.openFile(filename, 'w') as fh_out:
            kwargs['input_node'] = info.object.data_node
            kwargs['output_node'] = fh_out.root

            # Create a progress dialog that keeps the user up-to-date on what's
            # going on since this is a fairly lengthy process.
            dialog = ProgressDialog(title='Exporting data', 
                                    min=0,
                                    can_cancel=True,
                                    max=int(info.object.channel.shape[-1]),
                                    message='Initializing ...')

            # Define a function that, when called, updates the dialog ... 
            dialog.open()

            def callback(samples, max_samples, mesg):
                if samples == max_samples:
                    dialog.close()
                dialog.change_message(mesg)
                cont, skip = dialog.update(samples)
                return not cont
            
            # Run the extraction script
            extract_spikes(progress_callback=callback, **kwargs)

    def overlay_extracted_spikes(self, info):
        # Suggest a filename based on the filename of the original file (to make
        # it easier for the user to just click "OK").
        filename = re.sub(r'(.*?)(_raw)?\.(h5|hd5|hdf5)', r'\1_extracted.\3',
                          info.object.data_filename)

        # Get the output filename from the user
        dialog = FileDialog(action="open", 
                            wildcard='HDF5 file (*_extracted.hd5)|*_extracted.hd5|',
                            default_path=filename)
        dialog.open()
        if dialog.return_code != OK:
            return

        with tables.openFile(dialog.path, 'r') as fh:
            ts = fh.root.event_data.timestamps[:]
            channels = fh.root.event_data.channels[:]-1

            # If the user has already censored the spiketimes in the file, then
            # we can indicate which events have been "censored" here
            if 'censored' in fh.root.event_data:
                clusters = fh.root.event_data.censored[:]
                cluster_ids = [0, 1]
                cluster_types = [1, 4] # in process, garbage
            else:
                clusters = np.ones(len(channels))
                cluster_ids = [1]
                cluster_types = [1]
            overlay = ExtractedSpikeOverlay(timestamps=ts,
                                            channels=channels,
                                            clusters=clusters,
                                            cluster_ids=cluster_ids,
                                            cluster_types=cluster_types,
                                            plot=info.object.channel_plot)
            info.object.channel_plot.overlays.append(overlay)
            info.object.spike_overlays.append(overlay)

    def overlay_sorted_spikes(self, info):
        # Suggest a filename based on the filename of the original file (to make
        # it easier for the user to just click "OK").
        wildcard = re.sub(r'(.*?)(_raw)?\.(h5|hd5|hdf5)', r'\1_*_sorted.mat',
                          path.basename(info.object.data_filename))
        wildcard = 'MAT file (*_sorted.mat)|{}|'.format(wildcard)
        # Get the output filename from the user
        dialog = FileDialog(action="open", wildcard=wildcard)
        dialog.open()
        if dialog.return_code != OK:
            return

        with tables.openFile(dialog.path, 'r') as fh:
            ts = fh.root.unwrapped_times[:].ravel()
            channels = fh.root.channels[:].ravel()-1

            # Check to see if the data has been sorted yet.  If not, just mark
            # all the spikes as "in process".
            if 'assigns' in fh.root:
                clusters = fh.root.assigns[:].ravel()
                cluster_ids = fh.root.labels[0].ravel()
                cluster_types = fh.root.labels[1].ravel()
            else:
                clusters = np.ones(len(channels))
                cluster_ids = [1]
                cluster_types = [1]

            overlay = ExtractedSpikeOverlay(timestamps=ts,
                                            channels=channels,
                                            clusters=clusters,
                                            cluster_ids=cluster_ids,
                                            cluster_types=cluster_types,
                                            plot=info.object.channel_plot)

            info.object.channel_plot.overlays.append(overlay)
            info.object.spike_overlays.append(overlay)

    def clear_spike_overlays(self, info):
        while info.object.spike_overlays:
            overlay = info.object.spike_overlays.pop()
            info.object.channel_plot.overlays.remove(overlay)

    def overlay_rms(self, info):
        # Suggest a filename based on the filename of the original file (to make
        # it easier for the user to just click "OK").
        wildcard = re.sub(r'(.*?)(_raw)?\.(h5|hd5|hdf5)', r'\1_rms.\3',
                          path.basename(info.object.data_filename))
        wildcard = 'HDF5 file (*_rms.hd5)|{}|'.format(wildcard)
        # Get the output filename from the user
        dialog = FileDialog(action="open", wildcard=wildcard)
        dialog.open()
        if dialog.return_code != OK:
            return

        fh = tables.openFile(dialog.path, 'r')
        mc = FileMultiChannel.from_node(fh.root.rms)

        value_mapper = LinearMapper(range=DataRange1D())
        index_mapper = LinearMapper(range=info.object.index_range)
        plot = MultiChannelPlot(source=mc, 
                                value_mapper=value_mapper,
                                index_mapper=index_mapper,
                                line_color='blue',
                                line_width=2.0)

        info.object.channel_plot.sync_trait('channel_spacing', plot)
        info.object.channel_plot.sync_trait('channel_offset', plot)
        info.object.channel_plot.sync_trait('channel_visible', plot)

        info.object.plot_container.add(plot)

    def _prepare_decimation_settings(self, info):
        kwargs = {}
        kwargs['q'] = np.floor(info.object.channel.fs/600.0)
        kwargs['N'] = 4
        return kwargs

    def decimate_waveform(self, info):
        outputfile = self._get_filename('decimated', info)
        if outputfile is None:
            return
        kwargs = self._prepare_decimation_settings(info)
        with tables.openFile(outputfile, 'w') as fh:
            kwargs['input_node'] = info.object.data_node
            kwargs['output_node'] = fh.root
            decimate_waveform(**kwargs)

    def queue_extraction(self, info):
        kwargs = self._prepare_extract_settings(info)
        if kwargs is None:
            return
        outputfile = self._get_filename('extracted', info)
        if outputfile is None:
            return
        file_info = {
            'input_file':   info.object.data_filename,
            'input_path':   info.object.data_pathname,
            'output_file':  outputfile,
            'output_path':  '/',
            }
        self._append_batchfile('extract_spikes', file_info, kwargs, info)

    def queue_decimation(self, info):
        outputfile = self._get_filename('decimated', info)
        if outputfile is None:
            return
        file_info = {
            'input_file':   info.object.data_filename,
            'input_path':   info.object.data_pathname,
            'output_file':  outputfile,
            'output_path':  '/',
            }
        kwargs = self._prepare_decimation_settings(info)
        self._append_batchfile('decimate_waveform', file_info, kwargs, info)

    def _get_filename(self, extension, info):
        # Suggest a filename based on the filename of the original file (to make
        # it easier for the user to just click "OK").
        filename = re.sub(r'(.*?)(_raw)?\.(h5|hd5|hdf5)',
                          r'\1_{}.\3'.format(extension),
                          info.object.data_filename)

        # Get the output filename from the user
        dialog = FileDialog(action="save as", 
                            wildcard='HDF5 file (*.hd5)|*.hd5|',
                            default_path=filename)
        dialog.open()
        if dialog.return_code != OK:
            return
        else:
            return dialog.path

    def _append_batchfile(self, fn, file_info, kwargs, info):
        with open(info.object.batchfile, 'ab') as fh:
            # Pickle is a framed protocol (i.e. we can dump multiple objects to
            # the same file and Pickle will insert a separator in between each
            # object).  This is a Python binary protocol and is not
            # human-readable (nor human-editable).  This file is purely meant
            # for one-time use.
            pickle.dump((fn, file_info, kwargs), fh)
        information(info.ui.control, "Appended job to batchfile")

    def set_lfp_filter_defaults(self, info):
        # Set the freq_hp as well in case the user selects bandpass after
        # selecting this action.
        defaults = {
            'diff_mode':        None,
            'filter_btype':    'lowpass',
            'filter_order':     4,
            'filter_freq_lp':   300,
            'filter_freq_hp':   30,
            'filter_type':      'butter',
        }
        info.object.trait_set(**defaults)

    def set_su_filter_defaults(self, info):
        # Set the freq_lp as well in case the user selects bandpass after
        # selecting this action.
        defaults = {
            'diff_mode':        'all good',
            'filter_btype':     'highpass',
            'filter_order':     8,
            'filter_freq_hp':   300,
            'filter_freq_lp':   6000,
            'filter_type':      'butter',
        }
        info.object.trait_set(**defaults)

    def set_raw_defaults(self, info):
        defaults = {
            'diff_mode':        None,
            'filter_pass':      None,
        }
        info.object.trait_set(**defaults)

    def goto_time(self, info):
        # Create a little prompt to allow the user to specify the time they
        # want.
        class TimeDialog(HasTraits):
            minute = Float(0)
            second = Float(0)
        td = TimeDialog()

        # Setting kind to 'livemodal' ensures that the next line of code is not
        # reached until the user explicitly closes the dialog.
        dlg = td.edit_traits(parent=info.ui.control, kind='livemodal')

        # The HasTraits.edit_trait() method returns an instance of the GUI
        # dialog.  The result attribute is True when the users selects "OK",
        # False otherwise.
        if dlg.result:
            seconds = td.minute*60 + td.second
            info.object.index_range.trigger = seconds

class PhysiologyReview(HasTraits):

    spike_overlays      = List(Instance('chaco.api.AbstractOverlay'),
                               transient=True)

    # Name of the HDF5 file containing the raw data
    data_filename       = File(transient=True)
    # Pathname of the experiment node in the HDF5 file
    data_pathname       = Str(transient=True)
    # Actual file node instance
    data_file           = Any(transient=True)
    # Actual PyTables node of the experiments file
    data_node           = Any(transient=True)

    batchfile           = File(transient=True)
    channel             = Instance('cns.channel.ProcessedMultiChannel', (),
                                   transient=True)

    plot_container      = Instance(Component, transient=True)
    channel_plot        = Instance(Component, transient=True)
    channel_settings    = List(Instance(ChannelSetting))
    plot_settings       = List(Instance(PlotSetting), transient=True)
    trial_data          = Any(transient=True)
    trial_selected      = Any(transient=True)
    index_range         = Instance(ChannelDataRange, transient=True)

    bad_channels        = Property(depends_on='channel_settings.bad')
    extract_channels    = Property(depends_on='channel_settings.extract')
    visible_channels    = Property(depends_on='channel_settings.+')
    thresholds          = Property(depends_on='channel_settings.threshold')
    artifact_thresholds = Property(depends_on='channel_settings.artifact_threshold')

    channel_dclicked        = Event
    channel_dclick_toggle   = CBool(False, transient=True)
    channel_dclick_cache    = Any

    # Settings.  Be sure to include setting=True to indicate the value should be
    # saved and loaded as needed.
    filter_order        = DelegatesTo('channel', setting=True)
    filter_btype        = DelegatesTo('channel', setting=True)
    filter_freq_hp      = DelegatesTo('channel', setting=True)
    filter_freq_lp      = DelegatesTo('channel', setting=True)
    filter_type         = DelegatesTo('channel', setting=True)

    diff_mode           = DelegatesTo('channel', setting=True)

    # Region used to compute the noise floor 
    std_lb              = Int(-1, setting=True) # lower bound (in samples)
    std_ub              = Int(-1, setting=True) # upper bound (in samples)

    # What to show
    artifact_overlay_visible    = CBool(True)
    threshold_overlay_visible   = CBool(True)

    def _trial_data_default(self):
        return []

    def _channel_dclicked_fired(self, event):
        setting, column = event
        if self.channel_dclick_toggle:
            # We are currently in dclick "mask" mode where the user is viewing
            # only a single channel that they dclicked.
            if setting.index in self.visible_channels:
                # Show all the channels that used to be visible before the
                # double click.
                self.visible_channels = self.channel_dclick_cache
                self.channel_dclick_cache = []
                self.channel_dclick_toggle = False
            else:
                # A different channel has been requested.  Show that one
                # instead.
                self.visible_channels = [setting.index]
        else:
            # Enter dclick mask mode and show only the double clicked channel.
            # Be sure to save a copy of the visible channel list first.
            self.channel_dclick_cache = self.visible_channels
            self.visible_channels = [setting.index]
            self.channel_dclick_toggle = True

    def _data_node_changed(self, node):
        raw = node.data.physiology.raw
        self.channel = ProcessedFileMultiChannel.from_node(raw) 

        # If this is not a modified trial log, let's back it up (call it
        # "original_trial_log", add a "valid" column and save it back as the
        # modified trial log.
        if 'valid' not in node.data.trial_log.colnames:
            tl = node.data.trial_log.read()
            tl = recfunctions.append_fields(tl, 'valid', np.ones(len(tl)))
            node.data.trial_log._f_rename('original_trial_log')
            self.data_file.createTable(node.data, 'trial_log', tl)

        self.trial_data = node.data.trial_log
        self._update_plot()

    def _index_range_default(self):
        return ChannelDataRange(span=6, trig_delay=0.5, update_mode='triggered')

    def _trial_selected_changed(self, trial):
        self.index_range.trigger = trial['start']

    def _get_visible_channels(self):
        channels = self.channel_settings
        return [ch.index for ch in channels if ch.visible and not ch.bad]

    def _set_visible_channels(self, visible):
        for channel in self.channel_settings:
            channel.visible = channel.index in visible

    def _get_bad_channels(self):
        return [ch.index for ch in self.channel_settings if ch.bad]

    def _set_bad_channels(self, bad):
        for setting in self.channel_settings:
            if setting.index in bad:
                setting.bad = True

    def _get_extract_channels(self):
        return [ch.index for ch in self.channel_settings if ch.extract]

    def _get_thresholds(self):
        return [ch.threshold for ch in self.channel_settings]

    def _get_artifact_thresholds(self):
        return [ch.artifact_threshold for ch in self.channel_settings]

    def _channel_settings_default(self):
        return [ChannelSetting(index=i) for i in range(16)]

    def _update_plot(self):
        # Padding is in left, right, top, bottom order.  This is the container
        # that houses all the plots that we want overlaid.  Note that each plot
        # could have their own X or Y axis (meaning the scales would not be
        # comparable), or they can share a common X or Y axis.  Typically, all
        # plots inside this container will share a common X (index) axis but
        # have their own Y (value) axis.
        container = OverlayPlotContainer(padding=[20, 20, 20, 50])

        # This is what determines the *visible* range on the screen.  As
        # mentioned above, this is the X-axis that is shared by all the plots
        index_mapper = LinearMapper(range=self.index_range)
        #self.index_mapper = index_mapper

        # We're not sure what data are available to plot (the data format has
        # changed over time and some data may have been added or removed).
        # We'll try to add the the data.  If it fails, we'll just move onto the
        # next dataset.  This should be able to handle both aversive and
        # appetitive experiments.
        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        self.plot_settings = []
        for name, format in CHANNEL_FORMAT.items():
            try:
                node = self.data_node.data.contact._f_getChild(name)
                if name.endswith('_TTL'):
                    plot_class = TTLPlot
                    source = FileChannel.from_node(node)
                elif name.endswith('_ts'):
                    plot_class = TimeseriesPlot
                    source = FileTimeseries.from_node(node)
                elif name.endswith('_epoch'):
                    plot_class = EpochPlot
                    source = FileEpoch.from_node(node)
                plot = plot_class(source=source, index_mapper=index_mapper,
                                  value_mapper=value_mapper, **format)
                container.add(plot)
                setting = PlotSetting(plot=plot, name=name)
                self.plot_settings.append(setting)
            except AttributeError:
                print '{} does not exist'.format(name)

        # Add the multichannel neurophysiology to the container.  This is done
        # last so it appears on *top* of the TTL plots.
        value_mapper = LinearMapper(range=DataRange1D())
        plot = ExtremesMultiChannelPlot(source=self.channel,
                                        index_mapper=index_mapper,
                                        value_mapper=value_mapper)
        
        # This tool is responsible for the mouse panning/zooming behavior
        tool = MultiChannelRangeTool(component=plot)
        plot.tools.append(tool)
        self.sync_trait('visible_channels', plot, 'channel_visible',
                        mutual=False)
        self.sync_trait('bad_channels', self.channel, mutual=False)

        # Show what channels are displayed
        overlay = ChannelNumberOverlay(plot=plot)
        plot.overlays.append(overlay)
        self.channel_plot = plot

        # Add the plot to the container (otherwise it won't be shown at all)
        container.add(plot)

        # Let's add some grids and a time axis.  The actual process is just a
        # bunch of "boilerplate" code, so this is a helper function that takes
        # care of it for us.
        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot, orientation='bottom', fraction=True)

        overlay = ThresholdOverlay(plot=plot, sort_signs=[True]*16,
                                   line_color='green')
        self.sync_trait('thresholds', overlay, 'sort_thresholds', mutual=False)
        self.sync_trait('extract_channels', overlay, 'sort_channels',
                        mutual=False)
        self.sync_trait('threshold_overlay_visible', overlay, 'visible')
        plot.overlays.append(overlay)

        overlay = ThresholdOverlay(plot=plot, sort_signs=[False]*16,
                                   line_color='red')
        self.sync_trait('artifact_thresholds', overlay, 'sort_thresholds',
                        mutual=False)
        self.sync_trait('extract_channels', overlay, 'sort_channels',
                        mutual=False)
        self.sync_trait('artifact_overlay_visible', overlay, 'visible')
        plot.overlays.append(overlay)

        self.plot_container = container

    physiology_view = View(
        HSplit(
            Tabbed(
                VGroup(
                    VGroup(
                        Item('artifact_overlay_visible', 
                             label='Show artifact thresholds?'),
                        Item('threshold_overlay_visible', 
                             label='Show spike thresholds?'),
                        label='View settings'
                    ),
                    VGroup(
                        Item('diff_mode', label='Differential mode'),
                        Item('filter_freq_hp', label='Highpass cutoff (Hz)'),
                        Item('filter_freq_lp', label='Lowpass cutoff (Hz)'),
                        Item('filter_order', label='Filter order'),
                        Item('filter_btype', label='Filter band type'),
                        Item('filter_type', label='Filter type'),
                        label='Preprocessing',
                    ),
                    Item('channel_settings', editor=channel_editor, width=350),
                    show_labels=False,
                    label='Channels',
                ),
                Item('trial_data', editor=trial_log_editor, show_label=False,
                     width=350),
            ),
            Item('plot_container', 
                editor=ComponentEditor(width=1000, height=800), 
                resizable=True),
            show_labels=False,
            ),
        resizable=True,
        height=0.9, 
        width=0.9,
        handler=PhysiologyReviewController(),

        menubar = MenuBar(
            Menu(
                ActionGroup(
                    Action(name='&Open file',
                           accelerator='Ctrl+O',
                           action='open_file'),
                    Action(name='&Create &batchfile',
                           action='create_batchfile'),
                    Action(name='Open &batchfile',
                           action='open_batchfile'),
                ),
                name='&File',
            ),
            Menu(
                ActionGroup(
                    Action(name='Save settings', 
                           action='save_settings',
                           tooltip='Save channel and filter settings',
                           accelerator='Ctrl+S',
                           enabled_when='object.data_node is not None'
                          ),
                    Action(name='Revert settings', 
                           action='load_settings',
                           accelerator='Ctrl+R',
                           enabled_when='object.data_node is not None',
                          ),
                    Action(name='Default settings', 
                           action='default_settings',
                           enabled_when='object.data_node is not None',
                          ),
                    Action(name='Copy settings', 
                           action='copy_settings',
                           enabled_when='object.data_node is not None',
                          ),
                ),
                ActionGroup(
                    Action(name='LFP filter defaults',
                           action='set_lfp_filter_defaults',
                           enabled_when='object.data_node is not None',
                          ),
                    Action(name='Single unit filter defaults',
                           action='set_su_filter_defaults',
                           enabled_when='object.data_node is not None',
                          ),
                    Action(name='No filtering',
                           action='set_raw_defaults',
                           enabled_when='object.data_node is not None',
                          ),
                ),
                ActionGroup(
                    Action(name='Goto time',
                           action='goto_time'),
                ),
                ActionGroup(
                    Action(name='Zoom to 1 second',
                           action='set_zoom_1'),
                    Action(name='Zoom to 2 seconds',
                           action='set_zoom_2'),
                    Action(name='Zoom to 4 seconds',
                           action='set_zoom_4'),
                    Action(name='Zoom to 8 seconds',
                           action='set_zoom_8'),
                    Action(name='Zoom to 16 seconds',
                           action='set_zoom_16'),

                ),
                ActionGroup(
                    Action(name='Overlay extracted spikes',
                           action='overlay_extracted_spikes',
                           enabled_when='object.data_node is not None'),
                    Action(name='Overlay sorted spikes',
                           action='overlay_sorted_spikes',
                           enabled_when='object.data_node is not None'),
                    Action(name='Clear spike overlays',
                           action='clear_spike_overlays',
                           enabled_when='object.data_node is not None'),
                ),
                ActionGroup(
                    Action(name='Overlay RMS', action='overlay_rms',
                           enabled_when='object.data_node is not None'),
                ),
                name='&Settings',
            ),
            Menu(
                ActionGroup(
                    Action(name='Show spectrum',
                           action='show_spectrum_plot'),
                ),
                ActionGroup(
                    Action(name='Compute signal std. dev.', 
                           action='compute_std',
                           accelerator='Ctrl+C',
                           enabled_when='object.data_node is not None'
                          ),
                    Action(name='Compute running RMS', 
                           action='compute_rms',
                           enabled_when='object.data_node is not None'
                          ),
                ),
                ActionGroup(
                    Action(name='Extract spikes',
                           action='extract_spikes',
                           accelerator='Ctrl+E',
                           enabled_when='object.data_node is not None ' + \
                                        'and len(object.extract_channels)',
                          ),
                    Action(name='Queue spike extraction',
                           action='queue_extraction',
                           enabled_when='object.data_node is not None ' + \
                                        'and object.batchfile ' + \
                                        'and len(object.extract_channels)',
                          ),
                ),
                ActionGroup(
                    Action(name='Decimate waveform',
                           action='decimate_waveform',
                           accelerator='Ctrl+D',
                           enabled_when='object.data_node is not None'),
                    Action(name='Queue decimation',
                           action='queue_decimation',
                           enabled_when='object.data_node and object.batchfile'),
                ),
                ActionGroup(
                    Action(name='Truncate waveform',
                           action='truncate_waveform',
                           enabled_when='object.data_node is not None'),
                    Action(name='Zero waveform',
                           action='zero_waveform',
                           enabled_when='object.data_node is not None'),
                ),
                name='&Actions',
            ),
        ),
        title='Physiology Review',
    )

def get_experiment_node_dialog(filename):
    '''
    Given a physiology experiment file with multiple experiments, prompt the
    user for the experiment they'd like to analyze.  If only one experiment is
    present, no prompt will be generated.

    filename : str or None
        File to obtain experiment from.  If None, extract the argument from
        sys.argv[1]

    returns : (filename, node path)
    '''
    class Dialog(HasTraits):
        experiment = Str
        options = List
        view = View(
            Item('experiment', 
                 style='custom',
                 editor=EnumEditor(name='options'),
                ),
            kind='modal',
            buttons=['OK', 'Cancel'],
        )

    with tables.openFile(filename, 'r') as fh:
        nodes = fh.root._f_listNodes()
        if len(nodes) == 1:
            return nodes[0]._v_pathname
        elif len(nodes) == 0:
            return ''

        options = []
        for node in nodes:
            try:
                trials = len(node.data.trial_log)
            except:
                trials = 0
            option = '{} trials: {}'.format(trials, node._v_name)
            options.append(option)
        dialog = Dialog(options=options)
        dialog.configure_traits()
        i = options.index(dialog.experiment)
        return nodes[i]._v_pathname

def get_save_filename(raw_filename, suggested_ending):
    # Suggest a filename based on the filename of the original file (to make
    # it easier for the user to just click "OK").
    search_pattern = r'(.*?)(_raw)?\.(h5|hd5|hdf5)'
    sub_pattern = r'\1_{}.\3'.format(suggested_ending)
    filename = re.sub(search_pattern, sub_pattern, raw_filename) 

    # Get the output filename from the user
    dialog = FileDialog(action="save as", 
                        wildcard='HDF5 file (*.hd5)|*.hd5|',
                        default_path=filename)
    dialog.open()
    if dialog.return_code != OK:
        return
    return dialog.path

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--parameters', nargs='+', type=str,
                        required=False)

    args = parser.parse_args()
    trial_log_editor.adapter.parameters = args.parameters
    review = PhysiologyReview()
    review.configure_traits()
