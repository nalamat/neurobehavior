from enthought.envisage.api import Plugin, ServiceOffer
from enthought.traits.api import List
from enthought.envisage.ui.action.api import Action, Group
from enthought.envisage.ui.workbench.api import WorkbenchActionSet
from enthought.pyface.action.api import Action as ActionClass
from enthought.pyface.workbench.api import TraitsUIView


from enthought.traits.api import HasTraits, List, Tuple, Str, Int
from enthought.traits.ui.api import TabularEditor, View, Item
from enthought.traits.ui.tabular_adapter import TabularAdapter

class CohortItem(HasTraits):

    name = Str
    id = Int
    Description = Str

class Cohort(HasTraits):

    description = Str()
    items = List(CohortItem)

    traits_view = View(
        Item('description', show_label=False),
        Item('items', 
             editor=TabularEditor(
                 adapter=TabularAdapter(columns=[("name", "name"), ("id", "id")]),
                 editable=False),
             show_label=False),
        )

class LoadCohortAction(ActionClass):

    name = 'Load Cohort'

    def perform(self, event):
        from enthought.pyface.api import confirm, YES
        if confirm(None, "Would you like to load the cohort?") == YES:
            items=[CohortItem(name='Red', id=1, description="Test"),
                   CohortItem(name='Green', id=2, description="Test"),
                   CohortItem(name='Blue', id=3, description="Test"),
                   CohortItem(name='Yellow', id=4, description="Test"),
                   CohortItem(name='Orange', id=5, description="Test"),
                  ]
            cohort = Cohort(description="Test Cohort", items=items)
            self.window.application.register_service(Cohort, cohort)
            view = TraitsUIView(id='cohort',
                                name=cohort.description,
                                obj=cohort)
            self.window.add_view(view)

class CohortActionSet(WorkbenchActionSet):

    groups = [Group(id="Cohort", path="MenuBar/File")]
    actions = [Action(path="MenuBar/File", group="Cohort",
                      class_name='plugins.cohort_plugin:LoadCohortAction')]

class CohortPlugin(Plugin):

    id = 'plugins.Cohort'
    name = 'Cohort'

    SERVICE_OFFERS = 'enthought.envisage.service_offers'
    ACTION_SETS = 'enthought.envisage.ui.workbench.action_sets'
    service_offers = List(contributes_to=SERVICE_OFFERS)
    action_sets = List([CohortActionSet], contributes_to=ACTION_SETS)

    def _service_offers_default(self):
        return [ServiceOffer(protocol='cns.data.type.Cohort', 
                             factory='cns.data.type.Cohort')]
