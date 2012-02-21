from enthought.chaco.api import BaseXYPlot
from enthought.enable.api import black_color_trait, LineStyle
from enthought.traits.api import Event, Float, Instance

class BaseChannelPlot(BaseXYPlot):
    '''
    Not meant for use as a stand-alone plot.  Provides the base properties and
    methods shared by all subclasses.
    '''

    source                  = Instance('cns.channel.Channel')
    fill_color              = black_color_trait
    line_color              = black_color_trait
    line_width              = Float(1.0)
    line_style              = LineStyle
    data_changed            = Event

    def _source_changed(self, old, new):
        # We need to call _update_index_mapper when fs changes since this method
        # precomputes the index value based on the sampling frequency of the
        # channel.
        if old is not None:
            old.on_trait_change(self._data_changed, "changed", remove=True)
            old.on_trait_change(self._data_added, "added", remove=True)
            old.on_trait_change(self._index_mapper_updated, "fs", remove=True)
        if new is not None:
            new.on_trait_change(self._data_changed, "changed", dispatch="new")
            new.on_trait_change(self._data_added, "added", dispatch="new")
            new.on_trait_change(self._index_mapper_updated, "fs", dispatch="new")

    def _data_added(self, bounds):
        # We need to be smart about the data added event.  If we're not tracking
        # the index range, then the data that has changed *may* be off-screen.
        # In which case, we're doing a *lot* of work to redraw the exact same
        # picture.
        data_lb, data_ub = bounds
        s_lb, s_ub = self.index_range.low, self.index_range.high
        if (s_lb <= data_lb < s_ub) or (s_lb <= data_ub < s_ub):
            self._invalidate_data()

    def _data_changed(self):
        self._invalidate_data()
