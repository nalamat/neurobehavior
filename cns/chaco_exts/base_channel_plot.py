from enthought.chaco.api import BaseXYPlot
from enthought.enable.api import black_color_trait, LineStyle
from enthought.traits.api import Event, Float, Instance

class BaseChannelPlot(BaseXYPlot):
    '''
    Not meant for use as a stand-alone plot.  Provides the base properties and
    methods shared by all subclasses.
    '''

    channel                 = Instance('cns.channel.Channel')
    fill_color              = black_color_trait
    line_color              = black_color_trait
    line_width              = Float(1.0)
    line_style              = LineStyle
    data_changed            = Event

    def _channel_changed(self, old, new):
        # We need to call _update_index_mapper when fs changes since the method
        # precomputes the index value based on the sampling frequency of the
        # channel.
        if old is not None:
            old.on_trait_change(self._data_changed, "updated", remove=True)
            old.on_trait_change(self._index_mapper_updated, "fs", remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, "updated", dispatch="new")
            new.on_trait_change(self._index_mapper_updated, "fs", dispatch="new")
