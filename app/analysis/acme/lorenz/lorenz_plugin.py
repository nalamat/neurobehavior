from enthought.envisage.api import Plugin, ServiceOffer
from enthought.traits.api import List
from enthought.envisage.ui.action.api import Action, Group
from enthought.envisage.ui.workbench.api import WorkbenchActionSet
from enthought.pyface.action.api import Action as ActionClass
from enthought.pyface.workbench.api import TraitsUIView

class LoadCohortAction(ActionClass):

    name = 'Load Cohort'
    def perform(self, event):
        from enthought.pyface.api import FileDialog, confirm, NO, error, OK
        from cns.data.io import load_cohort
        from cns.data.view.cohort import CohortView
        fd = FileDialog(action='open',
                        default_directory='c:/users/brad/desktop/BNB',
                        wildcard='*.cohort.hd5')
        if fd.open() ==  OK and fd.path <> '':
            if self.window.get_view_by_id(fd.path) is not None:
                return
            cohort = load_cohort(0, fd.path)
            view = TraitsUIView(id=fd.path,
                                name=cohort.description,
                                obj=CohortView(cohort=cohort),
                                view='simple_view')
            self.window.add_view(view)

class CohortActionSet(WorkbenchActionSet):

    groups = [Group(id="Cohort", path="MenuBar/File")]
    actions = [Action(path="MenuBar/File", group="Cohort",
                      class_name='acme.lorenz.lorenz_plugin:LoadCohortAction')]

class LorenzPlugin(Plugin):
    """
    """

    id = 'acme.lorenz'
    name = 'Lorenz'

    SERVICE_OFFERS = 'enthought.envisage.service_offers'
    ACTION_SETS = 'enthought.envisage.ui.workbench.action_sets'
    service_offers = List(contributes_to=SERVICE_OFFERS)
    action_sets = List(contributes_to=ACTION_SETS)

    def _service_offers_default(self):
        return [ServiceOffer(protocol='cns.data.type.Cohort', 
                             factory='cns.data.type.Cohort')]

    def _action_sets_default(self):
        return [CohortActionSet]
