from enthought.enable.api import Component, ComponentEditor
from enthought.chaco.api import LinearMapper, DataRange1D
from enthought.traits.ui.api import VGroup, HGroup, Item, Include, View, \
        InstanceEditor, RangeEditor
from enthought.traits.api import Instance, HasTraits, Float, DelegatesTo

from cns.chaco.helpers import add_default_grids, add_time_axis
from cns.chaco.channel_data_range import ChannelDataRange
from cns.chaco.extremes_channel_plot import ExtremesChannelPlot

import cns

class PhysiologyExperimentMixin(HasTraits):

    physiology_plot = Instance(Component)
    physiology_index_range = Instance(ChannelDataRange)
    physiology_value_range = Instance(DataRange1D, ())

    physiology_scale = Float(0.5e-3)
    physiology_visible = DelegatesTo('physiology_plot', 'visible')
    physiology_offset = DelegatesTo('physiology_plot', 'offset')
    physiology_spacing = DelegatesTo('physiology_plot', 'spacing')

    def _physiology_value_range_update(self):
        value = len(self.physiology_visible)*self.physiology_scale
        self.physiology_value_range.high_setting = value
        self.physiology_value_range.low_setting = 0

    def _physiology_visible_changed(self):
        self._physiology_value_range_update()

    def _physiology_scale_changed(self, value):
        self._physiology_value_range_update()

    def _generate_physiology_plot(self):
        self.physiology_index_range = ChannelDataRange(span=5, trig_delay=1,
                timeseries=self.data.physiology_ts,
                sources=[self.data.physiology_ram])

        index_mapper = LinearMapper(range=self.physiology_index_range)
        value_mapper = LinearMapper(range=self.physiology_value_range)
        plot = ExtremesChannelPlot(channel=self.data.physiology_ram, 
                index_mapper=index_mapper, value_mapper=value_mapper,
                padding=[20, 20, 50, 50], bgcolor='white')

        add_default_grids(plot, major_index=1, minor_index=0.25)
        add_time_axis(plot)
        self.physiology_plot = plot

    physiology_settings_group = VGroup(
            #Item('handler.physiology_toolbar', style='custom'),
            Item('paradigm', style='custom',
                editor=InstanceEditor(view='physiology_view')),
            Include('physiology_view_settings_group'),
            show_border=True,
            show_labels=False,
            )

    physiology_view_settings_group = VGroup(
            Item('object.physiology_index_range.update_mode', 
                label='Trigger mode'),
            Item('object.physiology_index_range.span',
                label='X span',
                editor=RangeEditor(low=0.1, high=10)),
            Item('object.physiology_index_range.trig_delay',
                label='Trigger delay',
                editor=RangeEditor(low=0.0, high=5.0)),
            Item('physiology_scale', label='Y span',
                editor=RangeEditor(low=0, high=5e-3)),
            Item('physiology_offset', label='Plot offset',
                editor=RangeEditor(low=0, high=5e-3)),
            Item('physiology_spacing', label='Plot spacing',
                editor=RangeEditor(low=0, high=5e-3)),
            label='Plot Settings',
            show_border=True,
            )

    physiology_view = View(
            HGroup(
                Include('physiology_settings_group'),
                Item('physiology_plot', editor=ComponentEditor(), width=1400,
                    resizable=True),
                show_labels=False,
                ),
            resizable=True,
            height=1,
            width=1,
            # Offset this view so it appears on the second monitor.  If there is
            # no second monitor, the views will overlap (oh well).
            x=cns.MONITOR_OFFSET,
            )
