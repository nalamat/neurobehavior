import logging
log = logging.getLogger()
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

from enthought.envisage.core_plugin import CorePlugin
from enthought.envisage.ui.workbench.workbench_plugin import WorkbenchPlugin
from enthought.envisage.ui.workbench.api import WorkbenchApplication

from enthought.envisage.api import Plugin, ServiceOffer
from enthought.envisage.ui.action.api import Action, Group
from enthought.envisage.ui.workbench.api import WorkbenchActionSet
from enthought.pyface.action.api import Action as ActionClass
from enthought.pyface.workbench.api import TraitsUIView

from enthought.traits.api import HasTraits, List, Tuple, Str, Int, \
        Instance, Property, Any
from enthought.traits.ui.api import TabularEditor, View, Item, VGroup
from enthought.traits.ui.tabular_adapter import TabularAdapter

class CohortItem(HasTraits):

    name = Str
    id = Int
    description = Str
    display_text = Property

    def _get_display_text(self):
        return '%s %d' % (self.name, self.id)

    traits_view = View(VGroup('name', 'id', 'description', style='readonly'))
    #readonly_view = View(Item('display_text', style='readonly'))

class Cohort(HasTraits):

    description = Str()
    items = List(CohortItem)
    selected = Instance(CohortItem)

    app = Any

    def _selected_changed(self, new):
        self.app.edit(new)

    cohort_view = View(
        Item('description', show_label=False, style='readonly'),
        Item('items', 
             editor=TabularEditor(
                 adapter=TabularAdapter(columns=[("name", "name"), 
                                                 ("id", "id")]),
                 editable=False,
                 selected='selected'),
             show_label=False),
        )

    selected_view = View('object.selected.display_text~')
    #selected_view = View('object.selected.name', 'object.selected.id',
    #                     'object.selected.description')

class LoadCohortAction(ActionClass):

    name = 'Load Cohort'

    def perform(self, event):
        from enthought.pyface.api import confirm, YES
        if confirm(None, "Would you like to load the cohort?") == YES:
            print "FOOBAR"
            log.debug('Added TRAITS VIEW')
            log.debug('Added SELECTED VIEW')
            items=[CohortItem(name='Red', id=1, description="Test"),
                   CohortItem(name='Green', id=2, description="Test"),
                   CohortItem(name='Blue', id=3, description="Test"),
                   CohortItem(name='Yellow', id=4, description="Test"),
                   CohortItem(name='Orange', id=5, description="Test"),
                  ]
            cohort = Cohort(description="Test Cohort", items=items,
                            selected=items[0])
            cohort.app = self.window
            self.window.application.register_service(Cohort, cohort)
            selected_view = TraitsUIView(id='seleted item',
                                         name=cohort.description + 'selected',
                                         obj=cohort,
                                         view='selected_view')
            self.window.add_view(selected_view)
            view = TraitsUIView(id='cohort',
                                name=cohort.description,
                                obj=cohort,
                                view='cohort_view')
            self.window.add_view(view)

class CohortActionSet(WorkbenchActionSet):

    groups = [Group(id="Cohort", path="MenuBar/File")]
    actions = [Action(path="MenuBar/File", group="Cohort",
                      class_name='__main__:LoadCohortAction')]

class CohortPlugin(Plugin):

    id = 'plugins.Cohort'
    name = 'Cohort'

    ACTION_SETS = 'enthought.envisage.ui.workbench.action_sets'
    action_sets = List([CohortActionSet], contributes_to=ACTION_SETS)

class AnalysisApplication(WorkbenchApplication):

    id   = 'analysis'
    name = 'Data Analysis'

if __name__ == '__main__':
    plugins = [
        CorePlugin(), 
        WorkbenchPlugin(), 
        CohortPlugin(), 
        ]
    AnalysisApplication(plugins=plugins).run()
