from __future__ import division

import numpy as np
from enthought.chaco.api import DataRange1D
from enthought.traits.api import Float, List, Instance, Enum

class ChannelDataRange(DataRange1D):

    sources         = List(Instance('cns.channel.Channel'))
    timeseries      = Instance('cns.channel.Timeseries')
    span            = Float(20)
    trig_delay      = Float(5)
    update_mode     = Enum('auto', 'auto full', 'triggered', 'triggered full')

    scroll_period   = Float(20)

    def _span_changed(self):
        self.refresh()

    def _trig_delay_changed(self):
        self.refresh()
        
    def _update_mode_changed(self):
        self.refresh()

    def get_max_time(self):
        bounds = [s.get_bounds()[1] for s in self.sources if s.get_size()>0]
        return 0 if len(bounds) == 0 else max(bounds)

    def refresh(self):
        '''
        Keep this very simple.  The user cannot change low/high settings.  If
        they use this data range, the assumption is that they've decided they
        want tracking.
        '''
        if self.update_mode == 'auto':
            # Update the bounds as soon as the data scrolls into the next span
            spans = self.get_max_time()//self.span
            high_value = (spans+1)*self.span
            low_value = high_value-self.span-self.trig_delay
        elif self.update_mode == 'auto full':
            # Don't update the bounds until we have a full span of data to display
            spans = self.get_max_time()//self.span
            high_value = spans*self.span
            low_value = high_value-self.span-self.trig_delay
        elif self.update_mode == 'triggered':
            # We want the lower bound of the range to be referenced to the
            # trigger itself.
            low_value = self.timeseries.latest()-self.trig_delay
            high_value = low_value+self.span
        elif self.update_mode == 'triggered full':
            # We want the lower bound of the range to be referenced to the
            # trigger, but we don't want it to update until we have collected
            # enough data to display across the full span of the plot.
            max_time = self.get_max_time()
            index = -1
            try:
                # Keep searching through the timestamps until we find one that
                # is within the range we want
                while True:
                    ts = self.timeseries[index]
                    high_value = ts+self.span
                    if high_value < self.get_max_time():
                        break
                    index -= 1
            except IndexError:
                high_value = self.timeseries.t0
            low_value = high_value-self.span-self.trig_delay

        # Important!  Don't update the values unless they are different.
        # Needlessly updating these values results in excessive screen redraws,
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
