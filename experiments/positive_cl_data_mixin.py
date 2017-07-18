from __future__ import division

import numpy as np
from scipy import stats
from traits.api import (HasTraits, Property, cached_property,
        on_trait_change)

class PositiveCLDataMixin(HasTraits):

    PLOT_VALUES = ('par_go_count', 'par_hit_frac', 'par_dprime')
