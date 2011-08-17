from __future__ import division
from math import floor, ceil
import numpy as np

from enthought.traits.api import HasTraits, Range, Tuple, Bool, Int, Str, \
        List, Instance, Property, cached_property, Button, Float, on_trait_change

from enthought.traits.ui.api import View, VGroup, HGroup, Item, Label, Include

from enthought.traits.ui.api import TableEditor, ObjectColumn, RangeEditor
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn

from cns.util import to_list

class ChannelSetting(HasTraits):

    number          = Int
    differential    = Str
    visible         = Bool(True)
    bad             = Bool(False)
    
    # Threshold for candidate spike used in on-line spike sorting
    spike_threshold = Float(0.0005)
    
    # Windows used for candidate spike isolation and sorting.
    spike_windows   = List(Tuple(Float, Float, Float), [])

channel_editor = TableEditor(
        show_row_labels=True,
        sortable=False,
        columns=[
            ObjectColumn(name='number', editable=False, width=10, label=''),
            CheckboxColumn(name='visible', width=10, label='V'), 
            CheckboxColumn(name='bad', width=10, label='B'),
            #ObjectColumn(name='spike_threshold', label='Threshold', width=20),
            ObjectColumn(name='differential'),
            ]
        )

class PhysiologyParadigmMixin(HasTraits):

    commutator_inhibit      = Bool(False, init=True, immediate=True)

    # Width of buttons in GUI
    WIDTH = -40

    # These are convenience buttons for quickly setting the differentials of
    # each channel.
    diff_none       = Button('None')
    diff_bundle     = Button('Bundle')
    diff_sagittal   = Button('Sagittal')
    diff_coronal    = Button('Coronal')
    diff_all        = Button('All')
    #diff_visible    = Bool(True)

    def _get_diff_group(self, channel, group):
        ub = int(ceil(channel/group)*group + 1)
        lb = ub - group
        diff = range(lb, ub)
        diff.remove(channel)
        #if self.diff_visible:
        diff = [d for d in diff if not self.channel_settings[d-1].bad]
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
        for channel in self.channel_settings:
            value = self._get_diff_group(channel.number, 16)
            channel.set(True, differential=value)

    diff_group = VGroup(
            HGroup(
                Item('diff_bundle', width=WIDTH),
                Item('diff_sagittal', width=WIDTH),
                Item('diff_coronal', width=WIDTH),
                Item('diff_all', width=WIDTH),
                Item('diff_none', width=WIDTH),
                #Item('diff_good', label='Only good?', show_label=True),
                show_labels=False,
                ),
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
            Item('ch_14', width=WIDTH),
            Item('ch_24', width=WIDTH),
            Item('ch_34', width=WIDTH),
            Item('ch_44', width=WIDTH),
            '_',
            Item('ch_18', width=WIDTH),
            Item('ch_28', width=WIDTH),
            '_',
            Item('all', width=WIDTH),
            Item('none', width=WIDTH),
            show_labels=False,
            )

    def _set_visible(self, channels):
        for ch in self.channel_settings:
            ch.visible = ch.number in channels and not ch.bad

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
        settings = self.channel_settings
        return [i for i, ch in enumerate(settings) if ch.visible]
    
    spike_thresholds = Property(depends_on='channel_settings.spike_threshold',
                                init=True, immediate=True)
    
    def _get_spike_thresholds(self):
        return [ch.spike_threshold for ch in self.channel_settings]

    # Generates the matrix that will be used to compute the differential for
    # the channels. This matrix will be uploaded to the RZ5.
    diff_matrix = Property(depends_on='channel_settings.differential',
                           init=True, immediate=True)

    @cached_property
    def _get_diff_matrix(self):
        n_chan = len(self.channel_settings)
        map = np.zeros((n_chan, n_chan))
        for channel in self.channel_settings:
            diff = to_list(channel.differential)
            if len(diff) != 0:
                sf = -1.0/len(diff)
                for d in diff:
                    map[channel.number-1, d-1] = sf
            map[channel.number-1, channel.number-1] = 1
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
                Item('commutator_inhibit', label='Inhibit commutator?'),
                Include('filter_group'),
                Include('monitor_group'),
                Include('visible_group'),
                Include('diff_group'),
                Item('channel_settings', editor=channel_editor),
                show_labels=False,
                )
            )
