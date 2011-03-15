from __future__ import division
from math import floor, ceil
import numpy as np

from enthought.traits.api import HasTraits, Range, Tuple, Bool, Int, Str, \
        List, Instance, Property, cached_property, Button
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

    # These are convenience buttons for quickly setting the differentials of
    # each channel.
    diff_none       = Button('None')
    diff_bundle     = Button('Bundle')
    diff_sagittal   = Button('Sagittal')
    diff_coronal    = Button('Coronal')
    diff_all        = Button('All')

    def _get_diff_group(self, channel, group):
        ub = int(ceil(channel/group)*group + 1)
        lb = ub - group
        diff = range(lb, ub)
        print lb, ub, diff, channel
        diff.remove(channel)
        return ', '.join(str(ch) for ch in diff)

    def _diff_none_fired(self):
        for channel in self.channel_settings:
            channel.set(True, differential='')

    def _diff_bundle_fired(self):
        for channel in self.channel_settings:
            value = self._get_diff_group(channel.number, 4)
            channel.set(True, differential=value)

    def _diff_sagittal_fired(self):
        for channel in self.channel_settings:
            value = self._get_diff_group(channel.number, 8)
            channel.set(True, differential=value)

    def _diff_all_fired(self):
        for channel in self.channel-settings:
            value = self._get_diff_group(channel.number, 16)
            channel.set(True, differential=value)

    diff_group = HGroup(
            Item('diff_bundle'),
            Item('diff_sagittal'),
            Item('diff_coronal'),
            Item('diff_all'),
            Item('diff_none'),
            show_labels=False,
            )

    # These are convenience buttons for selecting subgroups of channels for
    # display on the computer scren.

    # Groups of 4
    ch_14   = Button(label='1-4')
    ch_24   = Button(label='5-8')
    ch_34   = Button(label='9-12')
    ch_44   = Button(label='13-16')

    # Groups of 8
    ch_18   = Button(label='1-8')
    ch_28   = Button(label='9-16')

    # All
    all     = Button(label='All')
    none    = Button(label='None')

    visible_group = HGroup(
            Item('ch_14'),
            Item('ch_24'),
            Item('ch_34'),
            Item('ch_44'),
            '_',
            Item('ch_18'),
            Item('ch_28'),
            '_',
            Item('all'),
            Item('none'),
            show_labels=False,
            )

    def _set_visible(self, channels):
        for channel in self.channel_settings:
            channel.visible = channel.number in channels

    def _ch_14_fired(self):
        self._set_visible(range(1, 5))

    def _ch_24_fired(self):
        self._set_visible(range(5, 9))

    def _ch_34_fired(self):
        self._set_visible(range(9, 13))

    def _ch_44_fired(self):
        self._set_visible(range(13, 17))

    def _ch_18_fired(self):
        self._set_visible(range(1, 9))

    def _ch_28_fired(self):
        self._set_visible(range(9, 17))

    def _all_fired(self):
        self._set_visible(range(1, 17))

    def _none_fired(self):
        self._set_visible([])

    # The RZ5 has four DAC channels.  We can send each of these channels to an
    # oscilloscope for monitoring.  The first DAC channel (corresponding to
    # channel 9 in the RPvds file) is linked to the speaker.  Gain is multiplied
    # by a factor of 1000 before being applied to the corresponding channel.
    monitor_ch_1        = Range(1, 16, 1, init=True, immediate=True)
    monitor_ch_2        = Range(1, 16, 5, init=True, immediate=True)
    monitor_ch_3        = Range(1, 16, 9, init=True, immediate=True)
    monitor_ch_4        = Range(1, 16, 13, init=True, immediate=True)
    monitor_gain_1      = Range(0, 100, 50, init=True, immediate=True)
    monitor_gain_2      = Range(0, 100, 50, init=True, immediate=True)
    monitor_gain_3      = Range(0, 100, 50, init=True, immediate=True)
    monitor_gain_4      = Range(0, 100, 50, init=True, immediate=True)

    # Bandpass filter settings
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
                    map[channel.number-1, d-1] = sf
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
                Include('visible_group'),
                Include('diff_group'),
                Item('channel_settings', editor=channel_editor),
                show_labels=False,
                )
            )
