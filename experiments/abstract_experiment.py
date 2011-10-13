from datetime import datetime, timedelta

from enthought.traits.api import HasTraits, Any, Instance, Property, Bool
from enthought.traits.ui.api import View, Include, VGroup, Item, Tabbed

from cns.data.h5_utils import append_date_node, append_node

from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_data import AbstractExperimentData
from abstract_experiment_paradigm import AbstractExperimentParadigm

from enthought.traits.ui.key_bindings import KeyBinding, KeyBindings
from experiments.paradigm_menu import create_menubar

import logging
log = logging.getLogger(__name__)

from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter
from colors import color_names

class ContextAdapter(TabularAdapter):

    columns = [('Parameter'), ('Value'), ('Variable')]

    def get_image(self, obj, trait, row, column):
        if column == 0 and self.item[-2]:
            return '@icons:tuple_node'

    def get_width(self, obj, trait, column):
        return 100

    def get_bg_color(self, obj, trait, row):
        if self.item[-1]:
            return color_names['light green']
        else:
            return color_names['white']

context_editor = TabularEditor(adapter=ContextAdapter(), editable=False)

class AbstractExperiment(HasTraits):

    animal              = Any
    store_node          = Any
    exp_node            = Any
    data_node           = Any

    paradigm            = Instance(AbstractExperimentParadigm, store='child')
    data                = Instance(AbstractExperimentData, store='child')
    start_time          = Instance(datetime, store='attribute')
    stop_time           = Instance(datetime, store='attribute')
    duration            = Property(store='attribute')
    date                = Property(store='attribute', depends_on='start_time')

    spool_physiology    = Bool(False)

    def _get_date(self):
        if self.start_time is None:
            return datetime.now()
        else:
            return self.start_time.date()

    def _get_duration(self):
        if self.start_time is None:
            return timedelta()
        elif self.stop_time is None:
            return datetime.now()-self.start_time
        else:
            return self.stop_time-self.start_time

    key_bindings = KeyBindings(
        KeyBinding(binding1='Ctrl-r', method_name='start'),
        )

    traits_group = VGroup(
            Item('handler.toolbar', style='custom'),
            Tabbed(
                Item('handler.tracker', style='custom'),
                Item('paradigm', style='custom'),
                Item('handler.current_context', editor=context_editor),
                show_labels=False,
                ),
            show_labels=False,
            )

    context_group = VGroup(
            Item('handler.current_context_list', editor=context_editor),
            show_labels=False,
            label='Current Context',
            )

    traits_view = View(
            Include('traits_group'), 
            key_bindings=key_bindings,
            resizable=True, 
            menubar=create_menubar(),
            height=0.9, 
            width=0.9)
