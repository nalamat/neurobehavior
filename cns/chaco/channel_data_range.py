import numpy as np
#from enthought.chaco.abstract_data_range import AbstractDataRange
from enthought.chaco.api import AbstractDataRange, DataRange1D
from enthought.traits.api import Float, List, Instance

class ChannelDataRange(DataRange1D):

    sources      = List(Instance('cns.channel.Channel'))
    range        = Float(24)
    interval     = Float(20)

    def refresh(self):
        '''
        Keep this very simple.  The user cannot change low/high settings.  If
        they use this data range, the assumption is that they've decided they
        want tracking.
        '''
        bounds = [s.get_bounds()[1] for s in self.sources if s.get_size() > 0]
        if len(bounds) == 0:
            max_time = 0
        else:
            max_time = max(bounds)
        high_value = np.ceil(max_time/self.interval)*self.interval
        low_value = high_value-self.range
        if (self._low_value != low_value) or (self._high_value != high_value):
            self._low_value = low_value
            self._high_value = high_value
            self.updated = (low_value, high_value)

    def _sources_changed(self, old, new):
        self.refresh()
        for source in old:
            source.on_trait_change(self.refresh, 'updated', remove=True)
        for source in new:
            source.on_trait_change(self.refresh, 'updated')

    def _sources_items_changed(self, event):
        self.refresh()
        for source in event.removed:
            source.on_trait_change(self.refresh, 'updated', remove=True)
        for source in event.added:
            source.on_trait_change(self.refresh, 'updated')
