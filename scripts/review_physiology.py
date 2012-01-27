# This code will require Traits 4

from scipy import signal
import numpy as np
from os import path
import re

from pyface.api import FileDialog, OK, error, ProgressDialog
from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import LinearMapper, DataRange1D, OverlayPlotContainer
from enthought.traits.ui.api import VGroup, HGroup, Item, Include, View, \
        InstanceEditor, RangeEditor, HSplit, Tabbed, Controller, ShellEditor
from enthought.traits.api import Instance, HasTraits, Float, DelegatesTo, \
     Bool, on_trait_change, Int, on_trait_change, Any, Range, Event, Property,\
     Tuple, List, cached_property, Str, Dict

# Used for displaying the checkboxes for channel/plot visibility config
from enthought.traits.ui.api import TableEditor, ObjectColumn
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn
from enthought.traits.ui.menu import MenuBar, Menu, ActionGroup, Action

# Used for the trial log display
from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

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

CHUNK_SIZE = 5e7

fill_alpha = 0.25
line_alpha = 0.55
line_width = 0.5

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

    def init(self, info):
        self.model = info.object

    def export_klustakwik(self, info):
        #dialog = FileDialog(action="save as", wildcard='HDF5 file (*.hd5)')
        #dialog.open()
        #if dialog.return_code == OK:
        #    filename = path.join(dialog.directory, dialog.filename)
        #    print 'Saving to', filename
        #else:
        #    print 'Action aborted'
        #    return

        maxint = 2**15      # Data is stored as 16 bit integers
        maxval = 0.4e-3     # Expected range of voltages
        sf = maxint/maxval  # Scaling factor

        node = self.model.physiology_data
        channels = self.model.extract_channels

        # Create and open the files that will contain the exported data
        name_fmt = 'channel_{}.txt'
        handles = []
        for ch in channels:
            fh = open(name_fmt.format(ch), 'wb')
            handles.append(fh)

        dialog = ProgressDialog(title='Exporting data', 
                                max=node.n_chunks(CHUNK_SIZE),
                                can_cancel=True)
        dialog.open()

        # Now, iterate through the data in manageable chunks and save each chunk
        for i, chunk in enumerate(node.chunk_iter(CHUNK_SIZE, channels)):
            # Ensure that the raw signal fills the full possible int16 range
            # for maximum resolution of the signal in KlustaKwik's sorting
            # algorithm, then convert to an int16.
            chunk *= sf
            chunk = chunk.astype('int16')

            # The chunk is a 2D array representing the extracted channels.  Save
            # each individual channel to the correct file.
            for fh, w in zip(handles, chunk):
                w.tofile(fh)

            # The user can explicitly request to cancel the operation, in which
            # case we simply do not continue processing the remaining chunks.
            # The chunks currently stored in the file should, however, be valid
            # so we will leave the data intact.
            cont, skip = dialog.update(i+1)
            if not cont:
                break

        # Close the files we opened for writing and close the dialog
        for fh in handles:
            fh.close()
        dialog.close()

    def export_ums_2000(self, info):
        dialog = FileDialog(action="save as", wildcard='HDF5 file (*.hd5)')
        dialog.open()
        if dialog.return_code == OK:
            filename = path.join(dialog.directory, dialog.filename)
        else:
            return

        node = self.model.physiology_data
        channels = self.model.extract_channels

        dialog = ProgressDialog(title='Exporting data',
                                max=node.n_chunks(CHUNK_SIZE), can_cancel=True)
        dialog.open()

        # Now, iterate through the data in manageable chunks and save each chunk
        with tables.openFile(filename, 'w') as fh:
            shape = (len(channels), node.n_samples)
            arr = fh.createCArray('/', 'signal', atom=tables.Float32Atom(),
                                  shape=shape)
            chunk_samples = node.chunk_samples(CHUNK_SIZE)
            for i, chunk in enumerate(node.chunk_iter(CHUNK_SIZE, channels)):
                # The chunk is a 2D array representing the extracted channels.
                # Save these to the CArray we created.
                s = i*chunk_samples
                arr[..., s:s+chunk_samples] = chunk

                # The user can explicitly request to cancel the operation, in
                # which case we simply do not continue processing the remaining
                # chunks.  The chunks currently stored in the file should,
                # however, be valid so we will leave the data intact.
                cont, skip = dialog.update(i+1)
                if not cont:
                    break
        dialog.close()

    def compute_std(self, info):
        node = self.model.physiology_data
        channels = self.model.extract_channels
        chunk_samples = int(node.chunk_samples(CHUNK_SIZE)*0.1)
        chunk = node[:,chunk_samples:2*chunk_samples]
        stdevs = np.median(np.abs(chunk)/0.6745, axis=1)
        for std, setting in zip(stdevs, self.model.channel_settings):
            setting.std = std

    def extract_spikes_ums(self, info):
        # Ensure that the noise floor computation is up-to-date
        self.compute_std(info)

        # There may be a lot of artifacts before or after the end of the
        # experiment due to removing the animal from the cage.
        ts_start = self.model.trial_data[0]['ts_start']
        ts_end   = self.model.trial_data[-1]['ts_end']

        # Set up the variables here.  We can eventually separate this out into a
        # stand-alone script or module that can be reused by non-GUI programs.
        settings = [s for s in self.model.channel_settings if s.extract]
        channels = np.array([s.index for s in settings])
        thresholds = np.array([s.threshold for s in settings])
        rej_thresholds = np.array([s.artifact_threshold for s in settings])
        stds = np.array([s.std for s in settings])

        node = self.model.physiology_data
        n_channels = len(settings)
        chunk_samples = node.chunk_samples(CHUNK_SIZE)
        fs = node.fs

        # Note that UMS2000 has a max_jitter option that will clip the waveform
        # used for sorting by that amount (e.g. the final window will be
        # window_size-max_jitter).  Be sure to include a little extra in the
        # extracted waveform that can be truncated.
        window_size = 2.1   # Window to extract (msec)
        cross_time = 0.5    # Alignment point for peak of waveform (msec)
        cov_samples = 5e3   # Number of samples to collect for estimating cov

        # Convert msec to number of samples
        #shadow_samples = int(np.ceil(shadow*fs*1e-3))
        window_samples = int(np.ceil(window_size*fs*1e-3))
        samples_before = int(np.ceil(cross_time*fs*1e-3))
        samples_after = window_samples-samples_before

        # The return statement forces an exit from this function, meaning
        # downstream code will not get executed. 
        if not len(channels):
            error(info.ui.control, 
                  'Must specify at least one channel to extract',
                  title='No channels selected')
            return

        # Suggest a filename based on the filename of the original file (to make
        # it easier for the user to just click "OK").
        filename = self.model.data_node._v_file.filename
        filename = re.sub(r'(.*)\.([h5|hd5|hdf5])', r'\1_extracted.\2',
                          filename)

        # Get the filename from the user
        dialog = FileDialog(action="save as", 
                            wildcard='HDF5 file (*.hd5)|*.hd5|',
                            default_path=filename)
        dialog.open()
        if dialog.return_code == OK:
            filename = path.join(dialog.directory, dialog.filename)
        else:
            return
        
        # Open the output datafile for writing.  The use of the with statement
        # ensures that special cleanup routines that properly close the HDF5
        # file are invoked in event of an error.
        with tables.openFile(filename, 'w') as fh:
            # First, create the nodes in the HDF5 file to store the data we
            # extract.

            # Ensure that underlying datatype of HDF5 array containing waveforms
            # is identical to the datatype of the source waveform (e.g. 32-bit
            # float).  EArrays are a special HDF5 array that can be extended
            # dynamically on-disk along a single dimension.
            size = (0, n_channels, window_samples)
            atom = tables.Atom.from_dtype(node.dtype)
            fh_waveforms = fh.createEArray('/', 'waveforms', atom, size)

            # Assuming a sampling rate of 12.5 kHz, storing indices as a 32-bit
            # integer allows us to locate samples in a continuous waveform of up
            # to 49.7 hours in duration.  This is more than sufficient for our
            # purpose (we will likely run into file size issues well before this
            # point anyway).
            fh_indices = fh.createEArray('/', 'timestamps', tables.Int32Atom(),
                                         (0,))
            
            # The actual channel the event was detected on.  We can represent up
            # to 32,767 channels with a 16 bit integer.  This should be
            # sufficient for at least the next year.
            fh_channels = fh.createEArray('/', 'channels', tables.Int16Atom(),
                                          (0,))

            # This is another way of determining which channel the event was
            # detected on.  Specifically, if we are saving waveforms from
            # channels 4, 5, 9, and 15 to the HDF5 file, then events detected on
            # channel 4 would be marked as 4 in /channels and 0 in /channels
            # index.  Likewise, events detected on channel 9 would be marked as
            # 3 in /channels_index.  This allows us to "slice" the /waveforms
            # array if needed to get the waveforms that triggered the detection
            # events.
            # >>> detected_waveforms = waveforms[:, channels_index, :]
            # This is also useful for UMS2000 becaues UMS2000 only sees the
            # extracted waveforms and assumes they are numbered consecutively
            # starting at 1.  By adding 1 to the values stored in this array,
            # this can be used for the event_channel data provided to UMS2000.
            fh_channel_indices = fh.createEArray('/', 'channel_indices',
                                                 tables.Int16Atom(), (0,))

            # We can represent up to 256 values with an 8 bit integer.  That's
            # overkill for a boolean datatype; however Matlab doesn't support
            # pure boolean datatypes in a HDF5 file.  Lame.  Artifacts is a 2d
            # array of [event, channel] indicating, for each event, which
            # channels exceeded the artifact reject threshold.
            size = (0, n_channels)
            fh_artifacts = fh.createEArray('/', 'artifacts', tables.Int8Atom(),
                                           size)

            # Save some metadata regarding the preprocessing of the data (e.g.
            # referencing and filtering) and feature extraction parameters.
            fh.setNodeAttr('/', 'fs', node.fs)
            fh.setNodeAttr('/', 'bad_channels', np.array(node.bad_channels))
            # Currently we only support one referencing mode (i.e. reference
            # against the average of the good channels) so I've hardcoded this
            # attribute for now.
            fh.setNodeAttr('/', 'reference_mode', 'all_good')
            fh.createArray('/', 'differential', node.diff_matrix)

            # Since we conventionally count channels from 1, convert our 0-based
            # index to a 1-based index.
            fh.setNodeAttr('/', 'extracted_channels', channels+1)
            fh.setNodeAttr('/', 'std', stds)

            # Be sure to save the filter coefficients used (not sure if this
            # is meaningful).  The ZPK may be more useful in general.
            # Unfortunately, HDF5 does not natively support complex numbers and
            # I'm not inclined to deal with the issue at present.
            fh.setNodeAttr('/', 'fc_lowpass', node.freq_lp)
            fh.setNodeAttr('/', 'fc_highpass', node.freq_hp)
            fh.setNodeAttr('/', 'filter_order', node.filter_order)

            b, a = node.filter_coefficients
            fh.setNodeAttr('/', 'filter_b', b)
            fh.setNodeAttr('/', 'filter_a', a)

            # Feature extraction settings
            fh.setNodeAttr('/', 'window_size', window_size)
            fh.setNodeAttr('/', 'cross_time', cross_time)
            fh.setNodeAttr('/', 'samples_before', samples_before)
            fh.setNodeAttr('/', 'samples_after', samples_after)
            fh.setNodeAttr('/', 'window_samples', window_samples)
            fh.setNodeAttr('/', 'threshold', thresholds)
            fh.setNodeAttr('/', 'reject_threshold', rej_thresholds)

            fh.setNodeAttr('/', 'experiment_range_ts', 
                           np.array([ts_start, ts_end]))

            # Create a progress dialog that keeps the user up-to-date on what's
            # going on since this is a fairly lengthy process.
            dialog = ProgressDialog(title='Exporting data', 
                                    max=node.n_chunks(CHUNK_SIZE),
                                    can_cancel=True,
                                    message='Initializing ...')
            dialog.open()

            # Allocate a temporary array, cov_waves, for storing the data used
            # for computing the covariance matrix required by UltraMegaSort2000.
            # Ensure that the datatype matches the datatype of the source
            # waveform.
            cov_waves = np.empty((cov_samples, n_channels, window_samples),
                                 dtype=node.dtype)

            # Start indices of the random waveform segments to extract for the
            # covariance matrix.  Ensure that the randomly selected start
            # indices are always <= (total number of samples in each
            # channel)-(size of snippet to extract) so we don't attempt to pull
            # out a snippet at the very end of the session.
            cov_indices = np.random.randint(0, node.n_samples-window_samples,
                                            size=cov_samples)

            # Sort cov_indices for speeding up the search and extract process
            # (each time we load a new chunk, we'll walk through cov_indices
            # starting at index cov_i, pulling out the waveform, then
            # incrementing cov_i by one until we hit an index that is sitting
            # inside the next chunk.
            cov_indices = np.sort(cov_indices)
            cov_i = 0

            thresholds = thresholds[:, np.newaxis]
            signs = np.ones(thresholds.shape)
            signs[thresholds < 0] = -1
            thresholds *= signs

            rej_thresholds = rej_thresholds[np.newaxis, :, np.newaxis]

            # Keep the user updated as to how many candidate spikes they're
            # getting
            tot_features = 0

            # Now, loop through the data in chunks, identifying the spikes in
            # each chunk and loading them into the event times file.  The
            # current chunk number is tracked as i_chunk
            iterable = node.chunk_iter(CHUNK_SIZE, channels, samples_before,
                                       samples_after)

            for i_chunk, chunk in enumerate(iterable):
                # Truncate the chunk so we don't look for threshold crossings in
                # the portion of the chunk that overlaps with the following
                # chunk.  This prevents us from attempting to extract partials
                # spikes.  Finally, flip the waveforms on the pertinent channels
                # (where we had a negative threshold requested) so that we can
                # perform the thresholding on all channels at the same time
                # using broadcasting.
                c = chunk[..., samples_before:-samples_after] * signs
                crossings = (c[..., :-1] <= thresholds) & (c[..., 1:] > thresholds)

                # Get the channel number and index for each crossing.  Be sure
                # to let the user know what's going on.
                channel_index, sample_index = np.where(crossings) 

                # Waveforms is likely to be reasonably large array, so
                # preallocate for speed.  It may actually be faster to just hand
                # it directly to PyTables for saving to the HDF5 file since
                # PyTables handles caching of writes.
                n_features = len(sample_index)
                waveforms = np.empty((n_features, n_channels, window_samples),
                                     dtype=node.dtype)

                # Loop through sample_index and pull out each waveform set.
                for w, s in zip(waveforms, sample_index):
                    w[:] = chunk[..., s:s+window_samples]
                fh_waveforms.append(waveforms)

                # Find all the artifacts and discard them.  First, check the
                # entire waveform array to see if the signal exceeds the
                # artifact threshold defined on any given sample.  Note that the
                # specified reject threshold for each channel will be honored
                # via broadcasting of the array.
                artifacts = (waveforms >= rej_thresholds) | \
                            (waveforms < -rej_thresholds)

                # Now, reduce the array so that we end up with a 2d array
                # [event, channel] indicating whether the waveform for any given
                # event exceed the reject threshold specified for that channel.
                artifacts = np.any(artifacts, axis=-1)
                fh_artifacts.append(artifacts)

                tot_features += len(waveforms)
                mesg = "Found {} features"
                dialog.change_message(mesg.format(tot_features))

                # The indices saved to the file must be referenced to t0.  Since
                # we're processing in chunks and the indices are referenced to
                # the start of the chunk, not the start of the experiment, we
                # need to correct for this.  The number of chunks processed is
                # stored in i_chunk.
                fh_indices.append(sample_index+i_chunk*chunk_samples)

                # Channel on which the event was detected
                fh_channels.append(channels[channel_index]+1)
                fh_channel_indices.append(channel_index)

                chunk_lb = i_chunk*chunk_samples
                chunk_ub = chunk_lb+chunk_samples
                while True:
                    if cov_i == cov_samples:
                        break
                    index = cov_indices[cov_i]
                    if index >= chunk_ub:
                        break
                    index = index-chunk_lb
                    cov_waves[cov_i] = chunk[..., index:index+window_samples]
                    cov_i += 1

                # Update the dialog each time we finish processing a chunk.  If
                # the user has hit the cancel button, cont (the first argument
                # returned) will be False and we should terminate the loop
                # immediately.
                cont, skip = dialog.update(i_chunk+1)
                if not cont:
                    break

            # If the user explicitly requested a cancel, compute the covariance
            # matrix only on the samples we were able to draw from the data.
            cov_waves = cov_waves[:cov_i]

            # Compute the covariance matrix in the format required by
            # UltraMegaSort2000 (note by Brad -- I don't fully understand the
            # intuition here, but this should be the correct format required).
            cov_waves.shape = cov_i, -1
            cov_matrix = np.cov(cov_waves.T)
            fh.createArray('/', 'covariance_matrix', cov_matrix)

    def extract_spikes(self, info):
        node = self.model.physiology_data
        channels = self.model.extract_channels
        settings = np.take(self.model.channel_settings, channels)
        n_channels = len(settings)
        chunk_samples = node.chunk_samples(CHUNK_SIZE)

        lb, ub = -10, 30
        samples = ub-lb
        cov_samples = 10e3

        # The return statement forces an exit from this function, meaning
        # downstream code will not get executed. 
        if not len(channels):
            error(info.ui.control, 
                  'Must specify at least one channel to extract',
                  title='No channels selected')
            return

        # Suggest a filename based on the filename of the original file (to make
        # it easier for the user to just click "OK").
        filename = self.model.data_node._v_file.filename
        filename = re.sub(r'(.*)\.([h5|hd5|hdf5])', r'\1_extracted.\2',
                          filename)

        # Get the filename from the user
        dialog = FileDialog(action="save as", wildcard='HDF5 file (*.hd5)',
                            default_path=filename)
        dialog.open()
        if dialog.return_code == OK:
            filename = path.join(dialog.directory, dialog.filename)
        else:
            return

        # Open the output datafile for writing.  The use of the with statement
        # ensures that special cleanup routines that properly close the HDF5
        # file are invoked in event of an error.
        with tables.openFile(filename, 'w') as fh:
            # First, create the nodes in the HDF5 file to store the data we
            # extract.
            handles = []

            for setting in settings:
                out = {}
                group = fh.createGroup('/', 'channel_{}'.format(setting.index))
                pathname = group._v_pathname
                out['waveforms'] = fh.createEArray(pathname, 'waveforms',
                        tables.Float32Atom(), (0, samples))
                out['indices'] = fh.createEArray(pathname, 'indices',
                        tables.Float32Atom(), (0,))

                # This is technically a boolean mask and could be stored using
                # the bitfield datatype; however, Matlab does not support this
                # so we are better off storing it as an integer for maximum
                # compatibility with Matlab.
                out['artifacts'] = fh.createEArray(pathname, 'artifacts',
                        tables.Int16Atom(), (0,))

                # Save some metadata regarding the preprocessing of the data
                # (e.g. referencing and filtering) and feature extraction
                # parameters.
                fh.setNodeAttr('/', 'fs', node.fs)
                fh.setNodeAttr('/', 'fc_lowpass', node.freq_lp)
                fh.setNodeAttr('/', 'fc_highpass', node.freq_hp)
                fh.createArray('/', 'differential', node.diff_matrix)

                # Save some additional metadata regarding the data
                fh.setNodeAttr(pathname, 'std', setting.std)

                # Be sure to save the filter coefficients used (not sure if this
                # is meaningful).  The ZPK may be more useful in general.
                b, a = node.filter_coefficients
                fh.createArray(pathname, 'filter_b', b)
                fh.createArray(pathname, 'filter_a', a)

                # Feature extraction settings
                fh.setNodeAttr(pathname, 'lb', lb)
                fh.setNodeAttr(pathname, 'ub', ub)
                fh.setNodeAttr(pathname, 'threshold', setting.threshold)
                fh.setNodeAttr(pathname, 'reject_threshold',
                               setting.artifact_threshold)

                handles.append(out)

            # Create a progress dialog that keeps the user up-to-date on what's
            # going on since this is a fairly lengthy process.
            dialog = ProgressDialog(title='Exporting data', 
                                    max=node.n_chunks(CHUNK_SIZE),
                                    can_cancel=True)
            dialog.open()

            # Allocate a temporary array, cov_waves, for storing the data used
            # for computing the covariance matrix required by UltraMegaSort2000
            cov_waves = np.empty((cov_samples, n_channels, samples))

            # Start indices of the random waveform segments to extract for the
            # covariance matrix.  Ensure that the randomly selected start
            # indices are always <= (total number of samples in each
            # channel)-(size of snippet to extract) so we don't attempt to pull
            # out a snippet at the very end of the session.
            cov_indices = np.random.randint(0, node.n_samples-samples,
                                            size=cov_samples)

            # Sort cov_indices for ease
            cov_indices = np.sort(cov_indices)
            cov_i = 0

            # Now, loop through the data in chunks, identifying the spikes in
            # each chunk and loading them into the event times file.
            for i, mc_chunk in enumerate(node.chunk_iter(CHUNK_SIZE, channels,
                                                         lbound=lb, rbound=ub)):
                for setting, chunk, out in zip(settings, mc_chunk, handles):
                    th = setting.threshold
                    rej_th = setting.artifact_threshold

                    # Don't look for threshold crossings in the overlapping
                    # portion that we requested from the adjacent chunk. 
                    # will be addressed when we process that one.  This also
                    # prevents us from attempting to extract a partial spike.
                    c = chunk[-lb:-ub]

                    if th > 0:
                        # Look for a positive crossing
                        crossings = (c[:-1] <= th) & (c[1:] > th)
                    else:
                        # Look for a negative crossing
                        crossings = (c[:-1] >= th) & (c[1:] < th)

                    # Loop through the indices of the threshold crossings,
                    # extract each feature, and save it to the datafile.  I
                    # don't believe there's a way to vectorize this for loop to
                    # my knowledge, but if we could do so there may be some
                    # significant speedups.  Hint, if Matlab could vectorize
                    # this code, then it can be vectorized in Python as well
                    # since Numpy's ndarray object is just as powerful (if not
                    # more so than) Matlab's array object.  Alternatively, one
                    # could Cythonize this code.
                    indices = np.flatnonzero(crossings)
                    n_features = len(indices)

                    # Waveforms is likely to be reasonably large array, so
                    # preallocate for speed
                    waveforms = np.empty((n_features, samples))

                    # Pull out the waveforms into our preallocated array
                    for k, j in enumerate(indices):
                        waveforms[k] = chunk[j:j+samples] 
                    out['waveforms'].append(waveforms)

                    # Check to see which features meet or exceed the reject
                    # threshold
                    if rej_th > 0:
                        artifacts = np.any(waveforms > rej_th, axis=1)
                    else:
                        artifacts = np.any(waveforms < rej_th, axis=1)
                    out['artifacts'].append(artifacts)

                    # Index must be referenced to t0.  Since we're processing in
                    # chunks and the indices are referenced to the start of the
                    # chunk, not the start of the experiment, we need to correct
                    # for this.  The number of chunks processed is stored in i.
                    out['indices'].append(indices+i*chunk_samples)

                    chunk_lb = i*chunk_samples
                    chunk_ub = lb+chunk_samples
                    mask = (cov_indices >= chunk_lb) & (cov_indices < chunk_ub)
                    for index in cov_indices[mask]:
                        index = index-chunk_lb+lb
                        cov_waves[cov_i] = chunk[index:index+samples]
                        cov_i += 1

                # Update the dialog each time we finish processing a chunk.  If
                # the user has hit the cancel button, cont (the first argument
                # returned) will be False and we should terminate the loop
                # immediately.
                cont, skip = dialog.update(i+1)
                if not cont:
                    break

            # If the user explicitly requested a cancel, compute the covariance
            # matrix only on the samples we were able to draw from the data.
            cov_waves = cov_waves[:cov_i]

            # Compute the covariance matrix in the format required by
            # UltraMegaSort2000 (note by Brad -- I don't fully understand the
            # intuition here, but this should be the correct format required).
            cov_waves.shape = cov_i, -1
            cov_matrix = np.cov(cov_waves.T)
            fh.createArray('/', 'covariance_matrix', cov_matrix)

class PhysiologyReview(HasTraits):

    data_node           = Any
    physiology_data     = Instance('cns.channel.ProcessedMultiChannel')

    plot                = Instance(Component)
    channel_settings    = List(Instance(ChannelSetting))
    plot_settings       = List(Instance(PlotSetting))
    trial_data          = Any
    current_trial       = Any
    index_range         = Instance(ChannelDataRange)

    bad_channels        = Property(depends_on='channel_settings.bad')
    extract_channels    = Property(depends_on='channel_settings.extract')
    visible_channels    = Property(depends_on='channel_settings.+')
    thresholds          = Property(depends_on='channel_settings.threshold')
    artifact_thresholds = Property(depends_on='channel_settings.artifact_threshold')

    #index_mapper        = Any

    channel_dclicked        = Event
    channel_dclick_toggle   = Bool(False)
    channel_dclick_cache    = Any

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


    def _physiology_data_default(self):
        node = self.data_node.physiology.raw
        return ProcessedFileMultiChannel.from_node(node)

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

    def _get_extract_channels(self):
        return [ch.index for ch in self.channel_settings if ch.extract]

    def _get_thresholds(self):
        return [ch.threshold for ch in self.channel_settings]

    def _get_artifact_thresholds(self):
        return [ch.artifact_threshold for ch in self.channel_settings]

    def _channel_settings_default(self):
        return [ChannelSetting(index=i) for i in range(16)]

    def _trial_data_default(self):
        return self.data_node.trial_log.read()

    def _plot_default(self):
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

        return container

    physiology_view = View(
        HSplit(
            Tabbed(
                VGroup(
                    VGroup(
                        Item('object.physiology_data.freq_hp', 
                             label='Highpass cutoff (Hz)'),
                        Item('object.physiology_data.freq_lp', 
                             label='Lowpass cutoff (Hz)'),
                        label='Filter settings',
                    ),
                    Item('channel_settings', editor=channel_editor, width=150),
                    Item('plot_settings', editor=plot_editor, width=150),
                    show_labels=False,
                    label='Channels',
                ),
                Item('trial_data', editor=trial_log_editor, show_label=False),
            ),
            Item('plot', 
                editor=ComponentEditor(width=500, height=800), 
                resizable=True),
            #Item('shell', editor=ShellEditor()),
            show_labels=False,
            ),
        resizable=True,
        height=0.9, 
        width=0.9,
        handler=PhysiologyReviewController(),
        menubar = MenuBar(
            Menu(
                ActionGroup(
                    Action(name='Export KlustaKwik', action='export_klustakwik'),
                    Action(name='Export UltraMegaSort2000',
                           action='extract_spikes_ums'),
                    Action(name='Compute noise floor', action='compute_std'),
                    Action(name='Extract spikes', action='extract_spikes'),
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
    import tables
    filename, nodepath = get_experiment_node()
    import sys
    trial_log_editor.adapter.parameters = sys.argv[2:]
    with tables.openFile(filename, 'r', rootUEP=nodepath) as fh:
        review = PhysiologyReview(data_node=fh.root.data)
        review.configure_traits()
