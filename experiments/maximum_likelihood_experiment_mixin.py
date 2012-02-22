from enthought.traits.api import (HasTraits, Instance, List, Float,
                                  on_trait_change, Bool, Int, Any, Dict)
from enthought.traits.ui.api import View, VGroup, Item, HGroup

from enthought.chaco.api import (OverlayPlotContainer, DataRange1D, PlotAxis,
                                 ScatterPlot, LinearMapper, ArrayDataSource, LinePlot)
from enthought.chaco.tools.api import PanTool, ZoomTool

from enthought.enable.api import Component, ComponentEditor
import numpy as np

from enthought.chaco.function_data_source import FunctionDataSource
from cns import get_config
from .maximum_likelihood import p_yes

SIZE = (400, 400)
CHACO_AXES_PADDING = get_config('CHACO_AXES_PADDING')
numpoints = 500
TRACKS = 2
    
def _xfunc(low, high):
    dx = (high - low) / numpoints
    real_low = np.ceil(low/dx) * dx
    real_high = np.ceil(high/dx) * dx
    return np.linspace(real_low, real_high, numpoints)

class _MLDataSource(FunctionDataSource):
    
    a = Float(0)
    m = Float(0)
    k = Float(0)
    
    def set_coefficients(self, a, m, k):
        self.set(False, a=a, m=m, k=k)
        self.recalculate()
    
    @on_trait_change('data_range.updated')
    def recalculate(self):
        if self.data_range is not None:
            low, high = self.data_range.low, self.data_range.high
            x = _xfunc(low, high)
            new_array = p_yes(self.a, self.m, self.k, x)
            ArrayDataSource.set_data(self, new_array)
        else:
            self._data = np.array([], dtype='f')
    
class MaximumLikelihoodExperimentMixin(HasTraits):
            
    # Tracking sequence
    ml_track_plot = Instance('enthought.enable.api.Component')
    ml_track_data = List()
    
    # Best fit maximum likelihood plot
    ml_plot = Instance('enthought.enable.api.Component')
    ml_index = Instance(FunctionDataSource)
    ml_value = Instance(_MLDataSource)
    
    def _ml_track_data_default(self):
        sources = []
        for i in range(TRACKS):
            # Order is index, value, index_hit, value_hit, index_miss, value_miss
            source = (ArrayDataSource(), ArrayDataSource(), ArrayDataSource(),
                      ArrayDataSource(), ArrayDataSource(), ArrayDataSource())
            sources.append(source)
        return sources
    
    @on_trait_change('data.ml_par_seq')
    def _update_ml_track_plot(self):
        par_seq = self.data.ml_par_seq
        hit_seq = self.data.ml_hit_seq

        i, v, i_hit, v_hit, i_miss, v_miss = self.ml_track_data[0]
        indices = np.arange(len(par_seq))

        i.set_data(indices)
        v.set_data(par_seq)
        i_hit.set_data(indices[hit_seq])
        v_hit.set_data(par_seq[hit_seq])
        i_miss.set_data(indices[~hit_seq])
        v_miss.set_data(par_seq[~hit_seq])

    @on_trait_change('data.ml_coefficients')
    def _update_ml_plot(self):
        self.ml_value.set_coefficients(*self.data.ml_coefficients)
    
    def _ml_plot_default(self):
        container = OverlayPlotContainer(padding=CHACO_AXES_PADDING)
        index_range = DataRange1D()
        value_range = DataRange1D(low=0, high=1)
        index_mapper = LinearMapper(range=index_range)
        value_mapper = LinearMapper(range=value_range)
        
        # Add the datasources so the psychometric function derived from the
        # maximum likelihood estimator is always shown across the full range
        # of tested values
        for sources in self.ml_track_data:
            index_range.add(sources[1])

        # Create the datasources for the psychometric function
        self.ml_index = FunctionDataSource(data_range=index_range, func=_xfunc)
        self.ml_value = _MLDataSource(data_range=index_range)
        line = LinePlot(index=self.ml_index, value=self.ml_value,
                        index_mapper=index_mapper, value_mapper=value_mapper)
        line.overlays.append(PlotAxis(line, orientation='left', title='Yes probability'))
        line.overlays.append(PlotAxis(line, orientation='bottom', title='Parameter'))
        container.add(line)
        
        #line.tools.append(PanTool(line, constrain=True, constrain_key=None,
        #                          constrain_direction='x'))
        line.overlays.append(ZoomTool(line, axis='index', tool_mode='range'))
        return container

    def _ml_track_plot_default(self):
        container = OverlayPlotContainer(padding=CHACO_AXES_PADDING)
        index_range = DataRange1D()
        value_range = DataRange1D()
        index_mapper = LinearMapper(range=index_range)
        value_mapper = LinearMapper(range=value_range)
        
        for i, v, i_hit, v_hit, i_miss, v_miss in self.ml_track_data:
            index_range.add(i)
            value_range.add(v)
            kwargs = dict(index_mapper=index_mapper,
                          value_mapper=value_mapper)
            
            # The connecting line
            line = LinePlot(index=i, value=v, **kwargs)
            container.add(line)
            
            # Black for hit
            scatter = ScatterPlot(index=i_hit, value=v_hit, marker='circle',
                                  color='black', **kwargs)
            container.add(scatter)
            
            # Red for miss
            scatter = ScatterPlot(index=i_miss, value=v_miss, marker='circle',
                                  color='red', **kwargs)
            container.add(scatter)
            
        # Add the overlays to the last plot
        line.overlays.append(PlotAxis(line, orientation='left', title='Parameter'))
        line.overlays.append(PlotAxis(line, orientation='bottom', title='Trial number'))
        return container

    analysis_plot_group = HGroup(
        Item('ml_track_plot', editor=ComponentEditor(size=SIZE), height=400, width=400),
        Item('ml_plot', editor=ComponentEditor(size=SIZE)),
        show_labels=False,
        )
