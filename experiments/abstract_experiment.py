from datetime import datetime

from enthought.traits.api import HasTraits, Any, Instance, Property, Bool, \
        DelegatesTo
from enthought.traits.ui.api import View, Include

from cns.data.h5_utils import append_date_node, append_node

from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_data import AbstractExperimentData
from abstract_experiment_paradigm import AbstractExperimentParadigm
from physiology_experiment_mixin import PhysiologyExperimentMixin

from enthought.traits.ui.key_bindings import KeyBinding, KeyBindings

import logging
log = logging.getLogger(__name__)

class AbstractExperiment(PhysiologyExperimentMixin):

    animal              = Any
    store_node          = Any
    exp_node            = Any
    data_node           = Any

    data                = Instance(AbstractExperimentData, store='node')
    paradigm            = Instance(AbstractExperimentParadigm, store='node')

    start_time          = Instance(datetime, store='attribute')
    stop_time           = Instance(datetime, store='attribute')
    duration            = Property(store='attribute')

    def _get_date(self):
        return self.start_time.date()

    def _get_duration(self):
        if self.stop_time is None and self.start_time is None:
            return datetime.timedelta()
        elif self.stop_time is None:
            return datetime.now()-self.start_time
        else:
            return self.stop_time-self.start_time

    key_bindings = KeyBindings(
        KeyBinding(binding1='Ctrl-m', method_name='toggle_maximized'),
        KeyBinding(binding1='Ctrl-f', method_name='toggle_fullscreen'),
        KeyBinding(binding1='Ctrl-s', method_name='swap_screens'),
        KeyBinding(binding1='Ctrl-r', method_name='start'),
        )

    traits_view = View(
            Include('traits_group'), 
            key_bindings=key_bindings,
            resizable=True)
