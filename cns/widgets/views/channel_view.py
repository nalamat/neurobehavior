from cns.channel import Channel, MultiChannel, SnippetChannel
from cns.widgets.tools.zoom_tool import RLZoomTool
from cns.widgets.views.decimated_plot import ChannelDataSource, TimeSeries, \
    SharedTimeSeries, TTLTimeSeries
from enthought.chaco.api import ArrayPlotData, DataRange1D, PlotLabel, \
    LinePlot, LinearMapper, ArrayDataSource, PlotAxis, OverlayPlotContainer, \
    VPlotContainer, FilledLinePlot, BasePlotContainer, Plot
from enthought.chaco.tools.api import PanTool, SimpleZoom
from enthought.enable.api import ComponentEditor
from enthought.enable.base_tool import KeySpec
from enthought.traits.api import Instance, Str, CFloat, Bool, Dict, List, \
    on_trait_change, Int, DelegatesTo, HasTraits, Any, Button
from enthought.traits.ui.api import View, Item, CheckListEditor, VGroup
import numpy as np

class ChannelView(HasTraits):

    component   = Instance(BasePlotContainer)

    title       = Str('')
    data        = Instance(ArrayPlotData, args=())

    window      = CFloat(2.5e-4)

    visual_aids = Bool(True)

    index_range = Instance(DataRange1D)
    value_range = Instance(DataRange1D)

    value_min   = DelegatesTo('value_range', 'low_setting')
    value_max   = DelegatesTo('value_range', 'high_setting')

    index_label = 'Time (s)'
    value_label = 'Volts (v)'

    # Any real number will be smaller than infinity and greater than negative
    # infinity.  This assumes that the data is purely real (I'm assuming that
    # the call to bounds func has the NaNs and INFs filtered out).
    _low        = CFloat(np.inf)
    _high       = CFloat(-np.inf)

    def _value_range_default(self):
        return DataRange1D(bounds_func=self._bounds_func)

    def _bounds_func(self, data_low, data_high, margin, tight_bounds):
        self._low = min(self._low, data_low)
        self._high = max(self._high, data_high)
        return self._low, self._high

    def _index_range_default(self):
        return DataRange1D(low=-self.window, high=0)

    traits_view = View(Item('component', editor=ComponentEditor(), show_label=False))

class FFTView(ChannelView):

    channel = Instance(Channel)
    idx = Str
    val = Str

    def _component_default(self):
        component = Plot(
            data=self.data,
            padding=(75, 25, 25, 75), # LRTB
            fill_padding=True,
            bgcolor='white',
            border_visible=True,
            title=self.title,
            use_backbuffer=False,
            )
        #component.index_range = self.index_range
        #component.value_range = self.value_range

        '''
        index_label = PlotLabel(self.index_label,
                component=component,
                overlay_position='bottom'
                )
        value_label = PlotLabel(self.value_label,
                component=component,
                overlay_position='left',
                angle=90,
                )
        component.overlays.append(index_label)
        component.overlays.append(value_label)
        '''

        pan = PanTool(component)
        component.tools.append(pan)
        zoom = SimpleZoom(component,
                          whieel_zoom_step=0.25,
                          enter_zoom_key=KeySpec('z'),
                          tool_mode='range',
                          axis='index')
        zoom = ConstrainedZoomTool(component,
                                   wheel_zoom_step=0.25,
                                   enter_zoom_key=KeySpec('z'))
        component.overlays.append(zoom)
        return component

    def add(self, channel, *args, **kwargs):
        self.channel = channel
        freq, mag, phase = channel.fft()
        self.idx = self.data.set_data('', freq, True)
        self.val = self.data.set_data('', mag, True)
        self.component.plot((self.idx, self.val), *args, **kwargs)

    @on_trait_change('channel:updated')
    def update_data(self):
        freq, mag, phase = self.channel.fft()
        self.data.set_data(self.idx, freq)
        self.data.set_data(self.val, mag)

class OverlayChannelView(Plot):

    channels = List(Channel, [])

    def plot(self, channel, *args, **kw):
        if channel not in self.channels:
            self.channels.append(channel)
            index_name = self.data.set_data('', channel.t_windowed, True)
            value_name = self.data.set_data('', channel.signal_windowed, True)
            self.index_names[channel] = index_name
            self.value_names[channel] = value_name

    @on_trait_change('channels:updated')
    def update_signal(self, channel, name, new):
        value_name = self.value_names[channel]
        self.data.set_data(value_name, self._clean(channel.signal_windowed))

class TTLChannelView(ChannelView):

    channels = List(Any, [])

    idx_range = Instance(DataRange1D, kw=dict(low_setting=-10, high_setting=0))
    idx_map = Instance(LinearMapper)
    
    def _idx_map_default(self):
        return LinearMapper(range=self.idx_range)

    def _component_default(self):
        return VPlotContainer(
                resizable='hv',
                bgcolor='transparent',
                fill_padding=True,
                padding=10,
                spacing=25,
                stack_order='top_to_bottom',
                )

    def add(self, channel, *args, **kw):
        val_range = DataRange1D(low_setting=-1.5, high_setting=1.5)
        val_map = LinearMapper(range=val_range)
        plot = TTLTimeSeries(channel=channel,
                             index_mapper=self.idx_map,
                             value_mapper=val_map,
                             *args, **kw)
        self.component.add(plot)

class MultipleChannelView(ChannelView):

    channels = List(Any, [])
    index_names = Dict(Channel, Str, {})
    value_names = Dict(Channel, Str, {})
    clean_data = Bool(False)
    
    idx_range = Instance(DataRange1D, kw=dict(low_setting=-10, high_setting=0))
    idx_map = Instance(LinearMapper)
    
    def _idx_map_default(self):
        return LinearMapper(range=self.idx_range)
    
    val_range = Instance(DataRange1D, kw=dict(low_setting=0, high_setting=1.0))
    val_map = Instance(LinearMapper)
    
    def _val_map_default(self):
        return LinearMapper(range=self.val_range)

    def _component_default(self):
        component = OverlayPlotContainer(
            padding=(75, 25, 25, 75), # LRTB
            fill_padding=True,
            bgcolor='white',
            show_border=True,
            )

        index_label = PlotLabel(self.index_label,
                component=component,
                overlay_position='bottom'
                )
        value_label = PlotLabel(self.value_label,
                component=component,
                overlay_position='left',
                angle=90,
                )
        component.overlays.append(index_label)
        component.overlays.append(value_label)

        pan = PanTool(component)
        component.tools.append(pan)
        #zoom = ConstrainedZoomTool(component,
        #                           wheel_zoom_step=0.25,
        #                           enter_zoom_key=KeySpec('z'))
        #component.overlays.append(zoom)
        return component

    def add(self, channel, type='line', ch_index=None, *args, **kwargs):
        if (channel, ch_index) not in self.channels:
            self.channels.append((channel, ch_index))
            plot = TimeSeries(channel=channel, 
                              ch_index=ch_index,
                              index_mapper=LinearMapper(range=self.idx_range),
                              value_mapper=LinearMapper(range=self.val_range),
                              *args, **kwargs)
            self.component.add(plot)

class MultiChannelView(ChannelView):

    channel = Instance(MultiChannel)
    signal = Instance(Channel)
    components = Dict(Int, Any, {})
    available = List(Int)
    ch_ds = Instance(ChannelDataSource, ())
    
    available = List(Str, [])
    visible = List(Str, editor=CheckListEditor(name='available', cols=1))
    
    _1_to_8 = Button
    _9_to_16 = Button
    _all = Button
    
    traits_view = View([VGroup('visible{}@', '_1_to_8', '_9_to_16', '_all',
                               'object.ch_ds.reference',
                               show_labels=False),
                        Item('component{}', editor=ComponentEditor()), '-'],
                       height=600,
                       width=600,
                       resizable=True)
    
    idx_range = Instance(DataRange1D, kw=dict(low_setting=0, high_setting=4.0))
    idx_map = Instance(LinearMapper)
    
    def _idx_map_default(self):
        return LinearMapper(range=self.idx_range)
    
    def _activate_channels(self, lb, ub):
        self.visible = [str(i) for i in range(lb, ub+1)]
    
    def __1_to_8_fired(self):
        self._activate_channels(1, 8)
        
    def __9_to_16_fired(self):
        self._activate_channels(9, 16)
        
    def __all_fired(self):
        self._activate_channels(1, 16)

    def _component_default(self):
        return VPlotContainer(
                resizable='hv',
                bgcolor='transparent',
                fill_padding=True,
                padding=10,
                spacing=25,
                stack_order='top_to_bottom',
                )
        
    def _signal_changed(self, new):
        val_range = DataRange1D(low_setting=-1.5, high_setting=1.5)
        val_map = LinearMapper(range=val_range)
        plot = TimeSeries(channel=new, 
                          index_mapper=self.idx_map,
                          value_mapper=val_map,
                          padding_left=75,
                          reference='trigger',
                          )
        axis = PlotAxis(orientation='left', component=plot,
                        small_haxis_style=True, title='Signal')
        plot.overlays.append(axis)
        self.component.insert(0, plot)
        
    def _channel_changed(self, new):
        val_range = DataRange1D(low_setting=-3e-4, high_setting=3e-4)
        #val_range = DataRange1D(low_setting=-5, high_setting=5)
        self.available = [str(i+1) for i in range(new.channels)]
        self.ch_ds = ChannelDataSource(channel=new)
        
        for i in range(new.channels):
            #ch_ds = ChannelDataSource(channel=new.get_channel(i))
            val_map = LinearMapper(range=val_range)
            #plot = TimeSeries(channel_source=ch_ds, 
            plot = SharedTimeSeries(channel=self.ch_ds,
                              channel_index=i,
                              index_mapper=self.idx_map,
                              value_mapper=val_map,
                              padding_left=75)
            axis = PlotAxis(orientation='left', component=plot,
                            small_haxis_style=True, title='%d' % (i+1))
            plot.overlays.append(axis)
            zoom = RLZoomTool(component=plot)
            plot.tools.append(PanTool(component=plot, constrain=True, constrain_direction="x"))
            plot.overlays.append(zoom)
            self.component.add(plot)
            self.components[i] = plot
            
        self._axis = PlotAxis(orientation='bottom', mapper=self.idx_map, 
                              title='Post Trigger Time (s)')
        self.visible = self.available
        self.set_visible()

    @on_trait_change('visible[]')
    def set_visible(self):
        visible = [int(i) for i in self.visible]
        for i, component in self.components.items():
            if i+1 not in visible:
                try: self.component.remove(component)
                except RuntimeError: pass
            else:
                self.component.add(component)
        self.component.add(self._axis)
                
class AveragedChannelView(ChannelView):

    channel = Instance(SnippetChannel)
    index = Instance(ArrayDataSource)
    average_signal = Instance(ArrayDataSource)

    plots = List(LinePlot)
    average_plot = Instance(LinePlot)

    index_mapper = Instance(LinearMapper)
    value_mapper = Instance(LinearMapper)

    def _index_mapper_default(self):
        return LinearMapper(range=self.index_range)

    def _value_mapper_default(self):
        return LinearMapper(range=self.value_range)

    def _container_default(self):
        container = OverlayPlotContainer(
                fill_padding=True,
                padding=40,
                )

        ax = PlotAxis(orientation='bottom',
                mapper=self.index_mapper,
                component=container)
        container.overlays.append(ax)
        ax = PlotAxis(orientation='left',
                mapper=self.value_mapper,
                component=container)
        container.overlays.append(ax)

        return container

    def _channel_changed(self, channel):
        self.container.remove(*self.plots)
        self.index = ArrayDataSource(channel.t)

        for s in channel.signal:
            plot = LinePlot(index=self.index,
                            value=ArrayDataSource(s),
                            index_mapper=self.index_mapper,
                            value_mapper=self.value_mapper,
                            color='gray',
                            alpha=0.5,
                            )
            self.plots.append(plot)
            self.container.add(plot)

        if channel.buffered:
            self.average_signal = ArrayDataSource(channel.average_signal)
        else:
            # Right now the Chaco library does not deal well with NaN values.
            # Such values occur when there is no buffered data (i.e.
            # average_signal returns an array of NaN), so we check to see if any
            # data has been buffered.  If not, we simply set the average signal
            # to zero.
            self.average_signal = ArrayDataSource(np.zeros(channel.samples))

        plot = LinePlot(index=self.index,
                        value=self.average_signal,
                        index_mapper=LinearMapper(range=self.index_range),
                        value_mapper=LinearMapper(range=self.value_range),
                        color='black',
                        line_width=2,
                        )
        self.container.add(plot)
        self.average_plot = plot

    @on_trait_change('channel:updated')
    def update_signal(self, channel, name, info):
        remove, add = info

        if remove:
            self.container.remove(*self.plots[:remove])
            self.plots = self.plots[remove:]

        if add:
            for s in channel.signal[-add:]:
                plot = LinePlot(index=self.index,
                                value=ArrayDataSource(s),
                                index_mapper=LinearMapper(range=self.index_range),
                                value_mapper=LinearMapper(range=self.value_range),
                                color='gray',
                                alpha=0.5,
                                )
                self.plots.append(plot)
                self.container.add(plot)

        if add or remove:
            self.average_signal.set_data(channel.average_signal)
            self.container.raise_component(self.average_plot)

