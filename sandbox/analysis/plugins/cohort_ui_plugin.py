from enthought.envisage.api import Plugin
from enthought.pyface.workbench.api import Perspective, PerspectiveItem
from enthought.pyface.workbench.api import TraitsUIView
from enthought.traits.api import List

class CohortPerspective(Perspective):
    """ A perspective containing the default analysis views. """
    
    name             = 'Cohort Perspective'
    show_editor_area = True

    contents = [
        PerspectiveItem(id='cohort.ui.simple'),
    ]

class CohortUIPlugin(Plugin):

    id = 'cohort.ui'
    name = 'Lorenz UI'

    # Extension points Ids.
    PERSPECTIVES   = 'enthought.envisage.ui.workbench.perspectives'
    VIEWS          = 'enthought.envisage.ui.workbench.views'
    perspectives   = List(contributes_to=PERSPECTIVES)
    views = List([], contributes_to=VIEWS)

    def _perspectives_default(self): 
        return [CohortPerspective]

    def _views_default(self):
        return [self._create_cohort_view]

    def _create_cohort_view(self, **traits):
        """ Factory method for the data view. """
        from cns.data.ui.cohort import CohortView
        cohort = self.application.get_service('cns.data.type.Cohort')
        view = TraitsUIView(id='cohort.ui.simple',
                            name=cohort.description,
                            obj=CohortView(cohort=cohort),
                            view='simple_view', 
                            **traits)
        return view
