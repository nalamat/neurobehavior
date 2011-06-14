import numpy as np

from physiology_data_mixin import PhysiologyDataMixin
from pump_data_mixin import PumpDataMixin

from enthought.traits.api import (List, Property, Tuple, cached_property, Any,
        Array, Int, Event)

EVENT_DTYPE = [('timestamp', 'i'), ('name', 'S64'), ('value', 'S128'), ]

from cns.data.h5_utils import get_or_append_node
from cns.channel import FileChannel
from cns.util.math import rcount

class AbstractExperimentData(PhysiologyDataMixin, PumpDataMixin):

    new_trial = Event

    def rcount(self, sequence):
        return rcount(sequence)

    def apply_mask(self, fun, masks, sequence):
        return np.array([fun(sequence[m]) for m in masks])

    def apply_par_mask(self, fun, sequence):
        return self.apply_mask(fun, self.par_mask, sequence)

    def _create_channel(self, name, dtype):
        contact_node = get_or_append_node(self.store_node, 'contact')
        return FileChannel(node=contact_node, name=name, dtype=dtype)

    def get_context(self):
        context_names = self.trait_names(context=True)
        return dict((t, getattr(self, t)) for t in context_names)

    # Node to store the data in
    store_node = Any

    # List of parameters to analyze.  If you set this up properly, then you can
    # re-analyze your data on the fly.
    parameters = List

    event_log = List(store='table', dtype=EVENT_DTYPE)

    def log_event(self, timestamp, name, value):
        self.event_log.append((timestamp, name, repr(value)))

    # Trial log structure
    _trial_log = List
    _trial_log_columns = Tuple
    trial_log = Property(store='table', depends_on='_trial_log')
    masked_trial_log = Property(depends_on='_trial_log')

    @cached_property
    def _get_trial_log(self):
        if len(self._trial_log) > 0:
            col_names = self._trial_log_columns
            return np.rec.fromrecords(self._trial_log, names=col_names)
        else:
            return []

    @cached_property
    def _get_masked_trial_log(self):
        return self.trial_log

    par_seq = Property(depends_on='trial_log, parameters')

    @cached_property
    def _get_par_seq(self):
        try:
            arr = np.empty(len(self.trial_log), dtype=object)
            arr[:] = zip(*[self.trial_log[p] for p in self.parameters])
            return arr
        except:
            return np.array([])

    def channel_from_buffer(self, buffer, channel_name):
        channel_trait = self.trait(channel_name)
        klass = channel_trait.trait_type.klass
        factory = channel_trait.trait_type.find_klass(klass)
        store_path = channel_trait.store_path
        dtype = channel_trait.dtype

        path, name = store_path.split('/')
        node = get_or_append_node(self.store_node, path)
        channel = factory(channels=buffer.channels, fs=buffer.fs, node=node,
                name=name, dtype=dtype)

        setattr(self, channel_name, channel)

    par_mask = Property(depends_on='trial_log, parameters')

    @cached_property
    def _get_par_mask(self):
        result = []
        # Numpy's equal function casts the argument on either side of the
        # operator to an array.  Numpy's default handling of tuples is to
        # convert it to an array where each element of the tuple is an element
        # in the array.  We need to do the casting ourself (e.g. ensure that we
        # have a single-element array where the element is a tuple).
        cmp_array = np.empty(1, dtype=object)
        for par in self.pars:
            cmp_array[0] = par
            m = self.par_seq == cmp_array 
            result.append(m)
        return result

    pars = Property(List(Int), depends_on='trial_log, parameters')

    @cached_property
    def _get_pars(self):
        # We only want to return pars for complete trials (e.g. ones for which a
        # go was presented).
        return np.unique(self.par_seq)

    def log_trial(self, **kwargs):
        names, record = zip(*sorted(kwargs.items()))
        if len(self.trial_log) == 0:
            self._trial_log_columns = names
            self._trial_log = [record]
        elif names == self._trial_log_columns:
            self._trial_log.append(record)
        else:
            raise ValueError, "Invalid log_trial attempt"
        self.new_trial = kwargs
