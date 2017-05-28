from datetime import datetime, timedelta

from traits.api import HasTraits, Any, Instance, Property, Bool
from traitsui.api import View, Include, VGroup, Item, Tabbed, TabularEditor
from traitsui.menu import MenuBar, Menu, ActionGroup, Action
from traitsui.tabular_adapter import TabularAdapter
from traitsui.key_bindings import KeyBinding, KeyBindings

from abstract_experiment_data import AbstractExperimentData
from abstract_experiment_paradigm import AbstractExperimentParadigm

from cns import get_config
color_names = get_config('COLOR_NAMES')

class ContextAdapter(TabularAdapter):

    columns = ['Parameter', 'Value', 'Variable']

    def get_image(self, obj, trait, row, column):
        if column == 0 and self.item[-2]:
            return '@icons:tuple_node'

    def get_width(self, obj, trait, column):
        return 100

    def get_bg_color(self, obj, trait, row, column=0):
        if self.item[-1]:
            return color_names['light green']
        else:
            return color_names['white']

context_editor = TabularEditor(adapter=ContextAdapter(), editable=False)

class AbstractExperiment(HasTraits):

    animal              = Any
    store_node          = Any
    experiment_node     = Any
    data_node           = Any

    paradigm            = Instance(AbstractExperimentParadigm)
    data                = Instance(AbstractExperimentData)

    spool_physiology    = Bool(False)

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
            resizable=True,
            menubar=MenuBar(
                Menu(
                    ActionGroup(
                        Action(name='Load paradigm', action='load_paradigm'),
                        Action(name='Save paradigm as', action='saveas_paradigm'),
                    ),
                    name='&Paradigm'),
            ),
            height=0.9,
            width=0.9)
