# This code will require Traits 4

from scipy import signal
import numpy as np

from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import LinearMapper, DataRange1D, OverlayPlotContainer
from enthought.traits.ui.api import VGroup, HGroup, Item, Include, View, \
        InstanceEditor, RangeEditor, HSplit, Tabbed, Controller
from enthought.traits.api import Instance, HasTraits, Float, DelegatesTo, \
     Bool, on_trait_change, Int, on_trait_change, Any, Range, Event, Property,\
     Tuple, List, cached_property, Str

# Used for displaying the checkboxes for channel/plot visibility config
from enthought.traits.ui.api import TableEditor, ObjectColumn
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn
from enthought.traits.ui.menu import MenuBar, Menu, ActionGroup, Action

# Used for the trial log display
from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

from cns.channel import ProcessedFileMultiChannel, FileChannel
from cns.chaco_exts.helpers import add_default_grids, add_time_axis
from cns.chaco_exts.channel_data_range import ChannelDataRange
from cns.chaco_exts.extremes_multi_channel_plot import ExtremesMultiChannelPlot
from cns.chaco_exts.ttl_plot import TTLPlot
from cns.chaco_exts.epoch_plot import EpochPlot
from cns.chaco_exts.channel_range_tool import MultiChannelRangeTool
from cns.chaco_exts.channel_number_overlay import ChannelNumberOverlay
from cns.chaco_exts.threshold_overlay import ThresholdOverlay

from experiments.colors import color_names

CHUNK_SIZE = 10e7

CHANNEL_FORMAT = {
    'spout_TTL':    {
        'fill_color':   (0.25, 0.41, 0.88, 0.5), 
        'line_width':   1,
        'rect_center':  0.25, 
        'rect_height':  0.2,
    },
    'signal_TTL':   {
        'fill_color':   (0, 0, 0, 0.5), 
        'line_color':   (0, 0, 0, 0.75),
        'line_width':   1, 
        'rect_height':   0.3, 
        'rect_center':  0.5,
    },
    'poke_TTL':     {
        'fill_color':   (.17, .54, .34, 0.5), 
        'rect_center':  0.75,
        'line_width':   1, 
        'rect_height':  0.2,
    },
    'reaction_TTL': {
        'fill_color':   (1, 0, 0, 0.5), 
        'line_color':   (1, 0, 0, 1),
        'line_width':   1, 
        'rect_height':  0.1, 
        'rect_center':  0.6,
    },
    'response_TTL': {
        'fill_color':   (0, 1, 0, 0.5), 
        'line_color':   (0, 1, 0, 1),
        'line_width':   1, 
        'rect_height':  0.1, 
        'rect_center':  0.5,
    },
    'reward_TTL': {
        'fill_color':   (0, 0, 1, 0.5), 
        'line_color':   (0, 0, 1, 1),
        'line_width':   1, 
        'rect_height':  0.1, 
        'rect_center':  0.4,
    },
    'TO_TTL':   {
        'fill_color':   (1, 0, 0, 0.5), 
        'line_color':   (1, 0, 0, 1),
        'line_width':   1, 
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

trial_log_editor = TabularEditor(editable=False, adapter=TrialLogAdapter(),
                                 selected='current_trial')

class ChannelSetting(HasTraits):

    index       = Int
    visible     = Bool(True)
    bad         = Bool(False)
    extract     = Bool(False)
    std         = Float(np.nan)

    # Convert to uV for displaying on-screen
    std_uv      = Property(Float, depends_on='std')
    threshold   = Property(Float, depends_on='std')

    # Array of event times (as indices)
    spikes      = Instance('cns.channel.SnippetChannel')
    n_spikes    = Property(Int, depends_on='spikes')

    @cached_property
    def _get_std_uv(self):
        return 10e6*self.std

    @cached_property
    def _get_threshold(self):
        return 5*self.std

    @cached_property
    def _get_n_spikes(self):
        return len(self.spikes)

channel_editor = TableEditor(
    columns=[ 
        ObjectColumn(name='index', width=10, label='#', editable=False),
        CheckboxColumn(name='visible', width=10, label='V'), 
        CheckboxColumn(name='bad', width=10, label='B'),
        CheckboxColumn(name='extract', width=10, label='E?'),
        ObjectColumn(name='n_spikes', width=25, label='# spikes',
                     editable=False),
        ObjectColumn(name='std_uv', width=75, label=u'\u03C3 (\u03BCV)',
                     editable=False),
        ]
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
        maxint = 2**15  # Data is stored as 16 bit integers
        maxval = 0.4e-3 # Expected range of voltages
        sf = maxint/maxval

        node = self.model.physiology_data
        channels = self.model.extract_channels
        with open('test.txt', 'w') as fh:
            for chunk in node.chunk_iter(CHUNK_SIZE, channels):
                print '... processing done, saving now'
                chunk *= sf
                np.savetxt(fh, chunk.T, fmt='%d', delimiter='\t')
                print '... saving done, processing now'
                break
        print 'Complete'

    def compute_std(self, info):
        node = self.model.physiology_data
        channels = self.model.extract_channels
        chunk_samples = node.chunk_samples(CHUNK_SIZE)
        chunk = node[:,chunk_samples:2*chunk_samples]
        print '... processing done'
        stdevs = np.median(np.abs(chunk)/0.6745, axis=1)
        print '... computed median'
        for std, setting in zip(stdevs, self.model.channel_settings):
            setting.std = std
        print 'Complete'

    def threshold_spikes(self, info):
        node = self.model.physiology_data
        channels = self.model.extract_channels
        # Pull out the thresholds we need, ensure that the resulting threshold
        # array is 2D (np.take returns a 1D array, np.newaxis adds a second
        # axis) and transform it.  Since each channel is stored as a separate
        # row in the multichannel array, we need to align the array holding
        # thresholds so that each threshold broadcasts to the correct channel.
        # To illustrate the ultimate goal ...
        #
        #       Channel waveform                StDev
        #
        # ch0 [[s0 s1 s2 s3 s4 s5 ... ]      [[ 0.32 ] 
        # ch1  [s0 s1 s2 s3 s4 s5 ... ]  >=   [ 0.37 ]
        # ch2  [s0 s1 s2 s3 s4 s5 ... ]]      [ 0.25 ]]
        #
        thresholds = np.take(self.model.thresholds, channels)[np.newaxis].T
        chunk_samples = node.chunk_samples(CHUNK_SIZE)

        ch_indices = []
        sp_indices = []
        sp_waveforms = []

        with tables.openFile('test.hd5', 'w') as fh:

            # First, create the nodes in the HDF5 file to store the data we
            # extract.
            waveform_nodes = []
            index_nodes = []
            for ch in channels:
                n = fh.createEArray('/', 'channel_{}'.format(ch+1),
                                    tables.Float32Atom(), (0, 40))
                waveform_nodes.append(n)
                n = fh.createEArray('/', 'channel_{}_indices'.format(ch+1),
                                    tables.Int32Atom(), (0,))
                index_nodes.append(n)

            # Now, loop through the data in chunks, identifying the spikes in
            # each chunk and loading them into the event times file.
            for i, chunk in enumerate(node.chunk_iter(CHUNK_SIZE, channels)):
                crossings = (chunk[..., :-1] <= thresholds) & \
                            (chunk[..., 1:] > thresholds)
                ch, indices = np.where(crossings)
                #ch_indices.append(ch)
                #sp_indices.append(indices + i*chunk_samples)

                for c, j in zip(ch, indices):
                    waveform = chunk[c, j-10:j+30]
                    # Make sure that the spike waveform did not cross a chunk
                    # boundary.  If it did, replace the waveform with an array of
                    # NaNs.  Eventually we can add some code to pull out the rest of
                    # the waveform from the next chunk.
                    if len(waveform) == 40:
                        waveform_nodes[c].append(waveform[np.newaxis])
                        index_nodes[c].append([j+i*chunk_samples])

        #ch_indices = np.concatenate(ch_indices)
        #sp_indices = np.concatenate(sp_indices)
        #sp_waveforms = np.vstack(sp_waveforms)

        ## Split up event times into their individual channels and save!  Note
        ## that (for efficiency reasons), we only pull out the channels we are
        ## analyzing.  Numpy.where only sees a single 2D array containing one row
        ## for each of the extracted channels; hence, ch_indices refers to the
        ## row in the 2D array.  We need to remap ch_indices to the actual
        ## channel number (e.g., if we extract 3, 4, 7, then they map to 0, 1,
        ## and 2, respectively in ch_indices).
        #for i, ch in enumerate(channels):
        #    indices = sp_indices[ch_indices==i]
        #    waveforms = sp_waveforms[ch_indices==i]
        #    self.model.channel_settings[ch].sp_indices = indices
        #    self.model.channel_settings[ch].sp_waveforms = waveforms

    def process_data(self, info):
        raw = self.model.data_node.physiology.raw
        b, a = self.model.plot.filter_coefficients
        diff = self.model.plot.diff_matrix

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

    #freq_lp             = DelegatesTo('physiology_data')
    #freq_hp             = DelegatesTo('physiology_data')

    def _physiology_data_default(self):
        node = self.data_node.physiology.raw
        return ProcessedFileMultiChannel.from_node(node)

    def _index_range_default(self):
        return ChannelDataRange(span=5, trig_delay=0)

    def _current_trial_changed(self, trial):
        self.index_range.trig_delay = -trial['start']+1

    def _get_visible_channels(self):
        channels = self.channel_settings
        return [ch.index-1 for ch in channels if ch.visible and not ch.bad]

    def _get_bad_channels(self):
        return [ch.index-1 for ch in self.channel_settings if ch.bad]

    def _get_extract_channels(self):
        return [ch.index-1 for ch in self.channel_settings if ch.extract]

    def _get_thresholds(self):
        return [ch.threshold for ch in self.channel_settings]

    def _channel_settings_default(self):
        return [ChannelSetting(index=i+1) for i in range(16)]

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

        # We're not sure what data are available to plot (the data format has
        # changed over time and some data may have been added or removed).
        # We'll try to add the the data.  If it fails, we'll just move onto the
        # next dataset.
        value_range = DataRange1D(low_setting=-0, high_setting=1)
        value_mapper = LinearMapper(range=value_range)
        for name, format in CHANNEL_FORMAT.items():
            try:
                node = self.data_node.contact._f_getChild(name)
                channel = FileChannel.from_node(node)
                plot = TTLPlot(channel=channel, index_mapper=index_mapper,
                               value_mapper=value_mapper, **format)
                container.add(plot)
                setting = PlotSetting(plot=plot, name=name)
                self.plot_settings.append(setting)
            except AttributeError, e:
                print '{} does not exist'.format(name)

        # Add the multichannel neurophysiology to the container.  This is done
        # last so it appears on *top* of the TTL plots.
        value_mapper = LinearMapper(range=DataRange1D())
        plot = ExtremesMultiChannelPlot(channel=self.physiology_data,
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

        overlay = ThresholdOverlay(plot=plot, sort_signs=[False]*16)
        self.sync_trait('thresholds', overlay, 'sort_thresholds', mutual=False)
        self.sync_trait('extract_channels', overlay, 'sort_channels',
                        mutual=False)
        plot.overlays.append(overlay)

        return container

    def process_data(self, info):
        print 'processing data', info

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
                    Action(name='Export KlustaKwik', action='export_klustakwik'),
                    Action(name='Compute noise floor', action='compute_std'),
                    Action(name='Threshold spikes', action='threshold_spikes'),
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
