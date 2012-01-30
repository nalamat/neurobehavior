# This code will require Traits 4

import tables
import cPickle as pickle
from scipy import signal
import numpy as np
from os import path
import re

from pyface.api import FileDialog, OK, error, ProgressDialog
from enable.api import Component, ComponentEditor
from chaco.api import LinearMapper, DataRange1D, OverlayPlotContainer
from chaco.tools.api import LineSegmentTool
from traitsui.api import VGroup, HGroup, Item, Include, View, \
        InstanceEditor, RangeEditor, HSplit, Tabbed, Controller, ShellEditor
from traits.api import Instance, HasTraits, Float, DelegatesTo, \
     Bool, on_trait_change, Int, on_trait_change, Any, Range, Event, Property,\
     Tuple, List, cached_property, Str, Dict

# Used for displaying the checkboxes for channel/plot visibility config
from traitsui.api import TableEditor, ObjectColumn
from traitsui.extras.checkbox_column import CheckboxColumn
from traitsui.menu import MenuBar, Menu, ActionGroup, Action

# Used for the trial log display
from traitsui.api import TabularEditor
from traitsui.tabular_adapter import TabularAdapter

from cns.channel import ProcessedFileMultiChannel, FileChannel, FileTimeseries
from cns.chaco_exts.helpers import add_default_grids, add_time_axis
from cns.chaco_exts.channel_data_range import ChannelDataRange
from cns.chaco_exts.extremes_multi_channel_plot import ExtremesMultiChannelPlot
from cns.chaco_exts.ttl_plot import TTLPlot
from cns.chaco_exts.epoch_plot import EpochPlot
from cns.chaco_exts.channel_range_tool import MultiChannelRangeTool
from cns.chaco_exts.channel_number_overlay import ChannelNumberOverlay
from cns.chaco_exts.threshold_overlay import ThresholdOverlay
from cns.chaco_exts.timeseries_plot import TimeseriesPlot

from experiments.colors import color_names
from extract_spikes import extract_spikes

fill_alpha = 0.25
line_alpha = 0.55
line_width = 0.5

CHUNK_SIZE = 5e7

CHANNEL_FORMAT = {
    'spout_TTL':    {
        'fill_color':   (0.25, 0.41, 0.88, fill_alpha), 
        'line_color':   (0.25, 0.41, 0.88, line_alpha), 
        'line_width':   line_width,
        'rect_center':  0.25, 
        'rect_height':  0.2,
    },
    'signal_TTL':   {
        'fill_color':   (0, 0, 0, fill_alpha), 
        'line_color':   (0, 0, 0, line_alpha),
        'line_width':   line_width, 
        'rect_height':  0.3, 
        'rect_center':  0.5,
    },
    'poke_TTL':     {
        'fill_color':   (.17, .54, .34, fill_alpha), 
        'line_color':   (.17, .54, .34, line_alpha), 
        'rect_center':  0.75,
        'line_width':   line_width, 
        'rect_height':  0.2,
    },
    'reaction_TTL': {
        'fill_color':   (1, 0, 0, fill_alpha), 
        'line_color':   (1, 0, 0, line_alpha),
        'line_width':   line_width, 
        'rect_height':  0.1, 
        'rect_center':  0.6,
    },
    'response_TTL': {
        'fill_color':   (0, 1, 0, fill_alpha), 
        'line_color':   (0, 1, 0, line_alpha),
        'line_width':   line_width, 
        'rect_height':  0.1, 
        'rect_center':  0.5,
    },
    'reward_TTL': {
        'fill_color':   (0, 0, 1, fill_alpha), 
        'line_color':   (0, 0, 1, line_alpha),
        'line_width':   line_width, 
        'rect_height':  0.1, 
        'rect_center':  0.4,
    },
    'TO_TTL':   {
        'fill_color':   (1, 0, 0, fill_alpha), 
        'line_color':   (1, 0, 0, line_alpha),
        'line_width':   line_width, 
        'rect_height':  0.1, 
        'rect_center':  0.1,
    },
}


class TrialLogAdapter(TabularAdapter):

    # List of tuples (column_name, field )
    columns = [ ('P',       'parameter'),
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

    parameters = List(Str)

    def _get_parameter_text(self):
        return ', '.join('{}'.format(self.item[p]) for p in self.parameters)

    def _get_speaker_text(self):
        return self.item['speaker'][0].upper()

    def _get_time_text(self):
        seconds = self.item['start']
        return "{0}:{1:02}".format(*divmod(int(seconds), 60))

    def _get_bg_color(self):
        if self.item['ttype'] == 'GO_REMIND':
            return color_names['dark green']
        elif self.item['ttype'] == 'GO':
            return color_names['light green']
        elif self.item['ttype'] == 'NOGO_REPEAT':
            return color_names['dark red']
        elif self.item['ttype'] == 'NOGO':
            return color_names['light red']

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

trial_log_editor = TabularEditor(editable=False, 
                                 adapter=TrialLogAdapter(),
                                 selected='current_trial')

class ChannelSetting(HasTraits):

    # Channel number (used for indexing purposes so this should be zero-based)
    index           = Int
    # Channel number (used for GUI purposes so this should be one-based)
    gui_index       = Property(depends_on='index')
    # Should the channel be plotted?
    visible         = Bool(True)
    # Is the channel bad?
    bad             = Bool(False)
    # Should this be included in the extracted data?
    extract         = Bool(False)
    # Noise floor (computed using the algorighm recommended by the spike sorting
    # article on scholarpedia)
    std             = Float(np.nan)
    # Standard deviations above the noise floor for candidate features
    th_std          = Float(-5.0)
    # Standard deviations above the noise floor to reject candidate 
    artifact_std    = Float(20.0)
    # Convert to uV for displaying on-screen
    std_mv          = Property(Float, depends_on='std')
    # Thresholds to use for spike extraction (can be NaN or Inf)
    threshold       = Property(Float, depends_on='std, th_std')
    # Threshold to use for artifact reject (based on deviation above noise floor)
    artifact_threshold = Property(Float, depends_on='std, artifact_std')
    # Timeseries of extracted features
    event_times     = Instance('cns.channel.Timeseries')

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
        ObjectColumn(name='gui_index', width=10, label='#', editable=False),
        CheckboxColumn(name='visible', width=10, label='V'), 
        CheckboxColumn(name='bad', width=10, label='B'),
        CheckboxColumn(name='extract', width=10, label='E?'),
        ObjectColumn(name='th_std', width=10, label='T'),
        ObjectColumn(name='artifact_std', width=10, label='A'),
        ObjectColumn(name='std_mv', width=75, label=u'\u03C3 (mV)',
                     format='%.3f', editable=False),
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

    def open_file(self, info):
        # Get the output filename from the user
        dialog = FileDialog(action="open", 
                            wildcard='HDF5 file (*.hd5)|*.hd5|')
        dialog.open()
        if dialog.return_code != OK:
            return
        if info.object.data_node and info.object.data_node._v_file.isopen:
            info.object.data_node._v_file.close()
        filename = path.join(dialog.directory, dialog.filename)
        filename, nodepath = get_experiment_node(filename)
        fh = tables.openFile(filename, 'a', rootUEP=nodepath)
        info.object.data_node = fh.root.data
        self.load_settings(info)

    def load_settings(self, info):
        node = info.object.data_node.physiology.raw
        settings = info.object.channel_settings
        channel = info.object.physiology_data
        try:
            channel.freq_lp = node._v_attrs['review_freq_lp']
            channel.freq_hp = node._v_attrs['review_freq_hp']
            channel.filter_order = node._v_attrs['review_filter_order']
            if 'bad_channels' in node._v_attrs:
                info.object.bad_channels = node._v_attrs['bad_channels']-1
            channel.diff_mode = node._v_attrs['review_diff_mode'] 
            extract_channels = node._v_attrs['review_extract_channels'] 
            for setting, extract in zip(settings, extract_channels):
                setting.extract = extract
            threshold_stds = node._v_attrs['review_threshold_stds'] 
            for setting, th_std in zip(settings, threshold_stds):
                setting.th_std = th_std
            rej_threshold_stds = node._v_attrs['review_rej_threshold_stds'] 
            for setting, rej_threshold_std in zip(settings, rej_threshold_stds):
                setting.artifact_std = rej_threshold_std
        except AttributeError:
            pass

    def save_settings(self, info):
        node = info.object.data_node.physiology.raw
        settings = info.object.channel_settings
        channel = info.object.physiology_data
        node._v_attrs['review_freq_lp'] = channel.freq_lp
        node._v_attrs['review_freq_hp'] = channel.freq_hp
        node._v_attrs['review_filter_order'] = channel.filter_order
        if len(channel.bad_channels):
            node._v_attrs['bad_channels'] = np.array(channel.bad_channels)+1
        node._v_attrs['review_diff_mode'] = channel.diff_mode
        extract_channels = np.array([s.extract for s in settings])
        node._v_attrs['review_extract_channels'] = extract_channels
        threshold_stds = np.array([s.th_std for s in settings])
        node._v_attrs['review_threshold_stds'] = threshold_stds
        rej_threshold_stds = np.array([s.artifact_std for s in settings])
        node._v_attrs['review_rej_threshold_stds'] = rej_threshold_stds

    def compute_std(self, info):
        lb = int(info.object.trial_data[0]['ts_start'])
        node = info.object.physiology_data
        channels = info.object.extract_channels
        chunk_samples = int(node.chunk_samples(CHUNK_SIZE))
        chunk = node[:,lb:lb+chunk_samples]
        stdevs = np.median(np.abs(chunk)/0.6745, axis=1)
        for std, setting in zip(stdevs, info.object.channel_settings):
            setting.std = std

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

        # Ensure that the noise floor computation is up-to-date
        self.compute_std(info)

        kwargs = {}

        # Compile our referencing and filtering instructions
        processing = {}
        processing['freq_lp'] = info.object.physiology_data.freq_lp
        processing['freq_hp'] = info.object.physiology_data.freq_hp
        processing['filter_order'] = info.object.physiology_data.filter_order
        processing['bad_channels'] = info.object.physiology_data.bad_channels
        processing['diff_mode'] = info.object.physiology_data.diff_mode

        # Set up the variables here.  We can eventually separate this out into a
        # stand-alone script or module that can be reused by non-GUI programs.
        kwargs['input_file'] = info.object.data_node._v_file.filename
        kwargs['experiment_path'] = info.object.data_node._v_file.rootUEP
        kwargs['processing'] = processing
        kwargs['noise_std'] = [s.std for s in settings]
        kwargs['channels'] = [s.index for s in settings]
        kwargs['threshold_stds'] = [s.th_std for s in settings]
        kwargs['rej_threshold_stds'] = [s.artifact_std for s in settings]
        kwargs['window_size'] = 2.1
        kwargs['cross_time'] = 0.5  
        kwargs['cov_samples'] = 5e3 

        return kwargs

    def extract_spikes(self, info):
        # Compile the necessary arguments to pass along to extract_spikes.  If
        # the helper method returns None, this means that there was a problem
        # with compiling the arguments (e.g. no channels were selected), so
        # return from the method.
        kwargs = self._prepare_extract_settings(info)
        if kwargs is None:
            return

        # Suggest a filename based on the filename of the original file (to make
        # it easier for the user to just click "OK").
        filename = info.object.data_node._v_file.filename
        filename = re.sub(r'(.*)\.([h5|hd5|hdf5])', r'\1_extracted.\2',
                          filename)

        # Get the output filename from the user
        dialog = FileDialog(action="save as", 
                            wildcard='HDF5 file (*.hd5)|*.hd5|',
                            default_path=filename)
        dialog.open()
        if dialog.return_code != OK:
            return
        kwargs['output_file'] = path.join(dialog.directory, dialog.filename) 
        kwargs['output_path'] = '/'

        # Create a progress dialog that keeps the user up-to-date on what's going on
        # since this is a fairly lengthy process.
        dialog = ProgressDialog(title='Exporting data', 
                                min=1,
                                max=100,
                                can_cancel=True,
                                message='Initializing ...')

        # Define a function that, when called, updates the dialog ... 
        dialog.open()
        def callback(pct, mesg):
            dialog.change_message(mesg)
            cont, skip = dialog.update(pct*100)
            return not cont

        extract_spikes(progress_callback=callback, **kwargs)

    def add_to_batchfile(self, info):
        kwargs = self._prepare_extract_settings(info)
        with open('batch_file.dat', 'ab') as fh:
            # Pickle is a framed protocol (i.e. we can dump multiple objects to
            # the same file and Pickle will insert a separator in between each
            # object).  This is a Python binary protocol and is not
            # human-readable (nor human-editable).  This file is purely meant
            # for one-time use.
            pickle.dump(kwargs, fh)

class PhysiologyReview(HasTraits):

    data_node           = Any(transient=True)
    physiology_data     = Instance('cns.channel.ProcessedMultiChannel', (),
                                   transient=True)

    plot                = Instance(Component, transient=True)
    channel_settings    = List(Instance(ChannelSetting))
    plot_settings       = List(Instance(PlotSetting), transient=True)
    trial_data          = Any(transient=True)
    current_trial       = Any(transient=True)
    index_range         = Instance(ChannelDataRange, transient=True)

    bad_channels        = Property(depends_on='channel_settings.bad')
    extract_channels    = Property(depends_on='channel_settings.extract')
    visible_channels    = Property(depends_on='channel_settings.+')
    thresholds          = Property(depends_on='channel_settings.threshold')
    artifact_thresholds = Property(depends_on='channel_settings.artifact_threshold')

    channel_dclicked        = Event
    channel_dclick_toggle   = Bool(False, transient=True)
    channel_dclick_cache    = Any

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
        raw = node.physiology.raw
        channel = ProcessedFileMultiChannel.from_node(raw,
                                                      filter_mode='lfilter')
        self.physiology_data = channel
        self.trial_data = node.trial_log.read()
        self._update_plot()

    def _index_range_default(self):
        return ChannelDataRange(span=5, trig_delay=0)

    def _current_trial_changed(self, trial):
        self.index_range.trig_delay = -trial['start']+1

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
                node = self.data_node.contact._f_getChild(name)
                channel = FileChannel.from_node(node)
                plot = TTLPlot(source=channel, index_mapper=index_mapper,
                               value_mapper=value_mapper, **format)
                container.add(plot)
                setting = PlotSetting(plot=plot, name=name)
                self.plot_settings.append(setting)
            except AttributeError, e:
                print '{} does not exist'.format(name)

        # Add the multichannel neurophysiology to the container.  This is done
        # last so it appears on *top* of the TTL plots.
        value_mapper = LinearMapper(range=DataRange1D())
        plot = ExtremesMultiChannelPlot(source=self.physiology_data,
                                        index_mapper=index_mapper,
                                        value_mapper=value_mapper)
        
        # This tool is responsible for the mouse panning/zooming behavior
        tool = MultiChannelRangeTool(component=plot)
        plot.tools.append(tool)
        self.sync_trait('visible_channels', plot, 'channel_visible',
                        mutual=False)
        self.sync_trait('bad_channels', self.physiology_data, mutual=False)

        # Show what channels are displayed
        overlay = ChannelNumberOverlay(plot=plot)
        plot.overlays.append(overlay)

        # Add the plot to the container (otherwise it won't be shown at all)
        container.add(plot)

        # Let's add some grids and a time axis.  The actual process is just a
        # bunch of "boilerplate" code, so this is a helper function that takes
        # care of it for us.
        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot, orientation='bottom')

        overlay = ThresholdOverlay(plot=plot, sort_signs=[True]*16,
                                   line_color='green')
        self.sync_trait('thresholds', overlay, 'sort_thresholds', mutual=False)
        self.sync_trait('extract_channels', overlay, 'sort_channels',
                        mutual=False)
        plot.overlays.append(overlay)

        overlay = ThresholdOverlay(plot=plot, sort_signs=[True]*16,
                                   line_color='red')
        self.sync_trait('artifact_thresholds', overlay, 'sort_thresholds',
                        mutual=False)
        self.sync_trait('extract_channels', overlay, 'sort_channels',
                        mutual=False)
        plot.overlays.append(overlay)
        #plot.overlays.append(LineSegmentTool(plot))

        self.plot = container

    physiology_view = View(
        HSplit(
            Tabbed(
                VGroup(
                    VGroup(
                        Item('object.physiology_data.freq_hp', 
                             label='Highpass cutoff (Hz)'),
                        Item('object.physiology_data.freq_lp', 
                             label='Lowpass cutoff (Hz)'),
                        Item('object.physiology_data.filter_order', 
                             label='Filter order'),
                        label='Filter settings',
                    ),
                    Item('channel_settings', editor=channel_editor, width=150),
                    #Item('plot_settings', editor=plot_editor, width=150),
                    show_labels=False,
                    label='Channels',
                ),
                Item('trial_data', editor=trial_log_editor, show_label=False),
            ),
            Item('plot', 
                editor=ComponentEditor(width=500, height=800), 
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
                    Action(name='Open file',
                           action='open_file'),
                    Action(name='Save settings',
                           action='save_settings'),
                    Action(name='Extract spikes',
                           action='extract_spikes'),
                    Action(name='Add to batchfile',
                           action='add_to_batchfile'),
                    Action(name='Compute noise floor', 
                           action='compute_std'),
                ),
                name='&File',
            ),
        ),
        title='Physiology Review',
    )

def get_experiment_node(filename=None):
    '''
    Given a physiology experiment file with multiple experiments, prompt the
    user for the experiment they'd like to analyze.  If only one experiment is
    present, no prompt will be generated.

    filename : str or None
        File to obtain experiment from.  If None, extract the argument from
        sys.argv[1]

    returns : (filename, node path)
    '''
    if filename is None:
        import sys
        filename = sys.argv[1]

    with tables.openFile(filename, 'r') as fh:
        nodes = fh.root._f_listNodes()
        if len(nodes) == 1:
            return filename, nodes[0]._v_pathname
        elif len(nodes) == 0:
            return ''

        while True:
            print 'Available experiments to analyze'
            for i, node in enumerate(nodes):
                try:
                    trials = len(node.data.trial_log)
                except:
                    trials = 0
                print '{}. {} trials: {}'.format(i, trials, node._v_name)

            ans = raw_input('Which experiment would you like to analyze? ')
            try:
                ans = int(ans)
                if 0 <= ans < len(nodes):
                    break
                else:
                    print 'Invalid option'
            except ValueError:
                print 'Please enter the number of the experiment'
        return filename, nodes[ans]._v_pathname

if __name__ == '__main__':
    import sys
    trial_log_editor.adapter.parameters = sys.argv[1:]
    review = PhysiologyReview()
    review.configure_traits()
