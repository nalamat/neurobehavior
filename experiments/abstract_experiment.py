from datetime import datetime

from enthought.traits.api import HasTraits, Any, Instance, Property
from enthought.traits.ui.api import View, Include, VGroup, Item, Tabbed

from cns.data.h5_utils import append_date_node, append_node

from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_data import AbstractExperimentData
from abstract_experiment_paradigm import AbstractExperimentParadigm
from physiology_experiment_mixin import PhysiologyExperimentMixin

from enthought.traits.ui.key_bindings import KeyBinding, KeyBindings

import logging
log = logging.getLogger(__name__)

from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter

class ContextAdapter(TabularAdapter):

    columns = [('Parameter'), ('Value')]

context_editor = TabularEditor(adapter=ContextAdapter(), editable=False)

class AbstractExperiment(PhysiologyExperimentMixin):

    animal              = Any
    store_node          = Any
    exp_node            = Any
    data_node           = Any

    data                = Instance(AbstractExperimentData, store='child')
    paradigm            = Instance(AbstractExperimentParadigm, store='child')

    start_time          = Instance(datetime, store='attribute')
    stop_time           = Instance(datetime, store='attribute')
    duration            = Property(store='attribute')
    date                = Property(store='attribute', depends_on='start_time')

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
        #KeyBinding(binding1='Ctrl-r', method_name='start'),
        )

    traits_group = VGroup(
            Item('handler.toolbar', style='custom'),
            Tabbed(
                Item('paradigm', style='custom'),
                Item('handler.current_context', editor=context_editor),
                show_labels=False,
                ),
            show_labels=False,
            )

    traits_view = View(
            Include('traits_group'), 
            key_bindings=key_bindings,
            resizable=True, 
            height=0.9, 
            width=0.9)
