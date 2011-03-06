import numpy as np

from enthought.traits.api import HasTraits, Range, Tuple, Bool, Int, Str, \
        List, Instance, Property, cached_property
from enthought.traits.ui.api import View, VGroup, HGroup, Item, Label, Include

from enthought.traits.ui.api import TableEditor, ObjectColumn, RangeEditor
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn

from cns.util import to_list

class ChannelSetting(HasTraits):

    number          = Int
    differential    = Str
    visible         = Bool(True)

channel_editor = TableEditor(
        show_row_labels=True,
        sortable=False,
        columns=[
            ObjectColumn(name='number', editable=False, width=10, label=''),
            CheckboxColumn(name='visible', width=10, label=''), 
            ObjectColumn(name='differential'),
            ]
        )

class PhysiologyParadigmMixin(HasTraits):

    monitor_ch_1        = Range(1, 16, 1, init=True, immediate=True)
    monitor_ch_2        = Range(1, 16, 5, init=True, immediate=True)
    monitor_ch_3        = Range(1, 16, 9, init=True, immediate=True)
    monitor_ch_4        = Range(1, 16, 13, init=True, immediate=True)
    monitor_gain_1      = Range(0, 100, 50, init=True, immediate=True)
    monitor_gain_2      = Range(0, 100, 50, init=True, immediate=True)
    monitor_gain_3      = Range(0, 100, 50, init=True, immediate=True)
    monitor_gain_4      = Range(0, 100, 50, init=True, immediate=True)
    monitor_fc_highpass = Range(0, 12.5e3, 300, init=True, immediate=True)
    monitor_fc_lowpass  = Range(0, 12.5e3, 10e3, init=True, immediate=True)

    channel_settings    = List(Instance(ChannelSetting))

    def _channel_settings_default(self):
        return [ChannelSetting(number=i) for i in range(1, 17)]

    # List of the channels visible in the plot
    visible_channels = Property(depends_on='channel_settings.visible',
            init=True, immediate=True)

    @cached_property
    def _get_visible_channels(self):
        return [i for i, ch in enumerate(self.channel_settings) if ch.visible]

    # Generates the matrix that will be used to compute the differential for the
    # channels.  This matrix will be uploaded to the RZ5.
    diff_matrix = Property(depends_on='channel_settings.differential',
            init=True, immediate=True)

    @cached_property
    def _get_diff_matrix(self):
        n_chan = len(self.channel_settings)
        map = np.zeros((n_chan, n_chan))
        for channel in self.channel_settings:
            channels = to_list(channel.differential)
            if len(channels) != 0:
                sf = -1.0/len(channels)
                for d in channels:
                    map[channel.number, d-1] = sf
        return map

    monitor_group = HGroup(
            VGroup(
                Label('Channel'),
                Item('monitor_ch_1'),
                Item('monitor_ch_2'),
                Item('monitor_ch_3'),
                Item('monitor_ch_4'),
                show_labels=False,
                ),
            VGroup(
                Label('Gain (1000x)'),
                Item('monitor_gain_1'),
                Item('monitor_gain_2'),
                Item('monitor_gain_3'),
                Item('monitor_gain_4'),
                show_labels=False,
                ),
            label='Monitor Settings',
            show_border=True,
            )

    filter_group = HGroup(
            Item('monitor_fc_highpass', style='text'),
            Label('to'),
            Item('monitor_fc_lowpass', style='text'),
            label='Filter Settings',
            show_labels=False,
            show_border=True,
            )

    physiology_view = View(
            VGroup(
                Include('filter_group'),
                Include('monitor_group'),
                Item('channel_settings', editor=channel_editor),
                show_labels=False,
                )
            )
