import numpy as np
import logging
log = logging.getLogger(__name__)

from enthought.traits.api import (List, Property, Tuple, cached_property, Any,
                                  Int, Event, HasTraits)


from cns.data.h5_utils import get_or_append_node
from cns.channel import FileChannel
from cns.util.math import rcount

def string_array_equal(a, string):
    if len(a) == 0:
        return np.array([], dtype='bool')
    else:
        return np.array(a) == string

class AbstractExperimentData(HasTraits):

    new_trial = Event

    def rcount(self, sequence):
        return rcount(sequence)

    def string_array_equal(self, array, string):
        return string_array_equal(array, string)

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

    event_log = Any

    def _event_log_default(self):
        file = self.store_node._v_file
        description = np.dtype([('timestamp', 'i'), ('name', 'S64'), 
                                ('value', 'S128'),])
        node = file.createTable(self.store_node, 'event_log', description)
        return node

    def log_event(self, timestamp, name, value):
        # The append() method of a tables.Table class requires a list of rows
        # (i.e. records) to append to the table.  Since we only append a single
        # row at a time, we need to nest it as a list that contains a single
        # record.
        self.event_log.append([(timestamp, name, repr(value))])

    # Trial log structure
    _trial_log = List
    _trial_log_columns = Tuple
    trial_log = Property(store='table', depends_on='_trial_log')

    @cached_property
    def _get_trial_log(self):
        if len(self._trial_log) > 0:
            col_names = self._trial_log_columns
            return np.rec.fromrecords(self._trial_log, names=col_names)
        else:
            return []

    par_seq = Property(depends_on='masked_trial_log, parameters')

    @cached_property
    def _get_par_seq(self):
        if len(self.masked_trial_log) != 0:
            arr = np.empty(len(self.masked_trial_log), dtype=object)
            arr[:] = zip(*[self.masked_trial_log[p] for p in self.parameters])
            return arr
        else:
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

    par_mask = Property(depends_on='masked_trial_log, parameters')

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

    pars = Property(List(Int), depends_on='masked_trial_log, parameters')

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
            log.debug("Expected the following columns %r", self._trial_log_columns)
            log.debug("Recieved the following columns %r", names)
            raise AttributeError, "Invalid log_trial attempt"
        self.new_trial = kwargs
