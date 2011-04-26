import numpy as np
from enthought.chaco.api import DataRange1D
from enthought.traits.api import Float, List, Instance, Enum

class ChannelDataRange(DataRange1D):

    sources         = List(Instance('cns.channel.Channel'))
    timeseries      = Instance('cns.channel.Timeseries')
    span            = Float(20)
    trig_delay      = Float(5)
    update_mode     = Enum('auto', 'triggered')

    def _span_changed(self):
        self.refresh()

    def _trig_delay_changed(self):
        self.refresh()
        
    def _update_mode_changed(self):
        self.refresh()

    def refresh(self):
        '''
        Keep this very simple.  The user cannot change low/high settings.  If
        they use this data range, the assumption is that they've decided they
        want tracking.
        '''
        if self.update_mode == 'auto':
            bounds = [s.get_bounds()[1] for s in self.sources if s.get_size()>0]
            max_time = 0 if len(bounds) == 0 else max(bounds)
            max_time += self.trig_delay
            high_value = np.ceil(max_time/self.span)*self.span-self.trig_delay
            low_value = high_value-self.span
        else:
            low_value = self.timeseries.latest()-self.trig_delay
            high_value = low_value + self.span

            if (self._low_value != low_value) or (self._high_value != high_value):
                self._low_value = low_value
                self._high_value = high_value
                self.updated = (low_value, high_value)

        # Important!  Don't update the values unless they are different.
        # Nedlessly updating these values results in excessive screen redraws,
        # computations, etc., since other components may be "listening" to
        # ChannelDataRange for changes to its bounds.
        if (self._low_value != low_value) or (self._high_value != high_value):
            self._low_value = low_value
            self._high_value = high_value
            self.updated = (low_value, high_value)

    def _sources_changed(self, old, new):
        for source in old:
            source.on_trait_change(self.refresh, 'updated', remove=True)
        for source in new:
            source.on_trait_change(self.refresh, 'updated')
        self.refresh()

    def _sources_items_changed(self, event):
        for source in event.removed:
            source.on_trait_change(self.refresh, 'updated', remove=True)
        for source in event.added:
            source.on_trait_change(self.refresh, 'updated')
        self.refresh()

    def _timeseries_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self.refresh, 'updated', remove=true)
        if new is not None:
            new.on_trait_change(self.refresh, 'updated')
        self.refresh()
