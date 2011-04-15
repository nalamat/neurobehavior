# Enthought library imports.
from enthought.envisage.api import Plugin
from enthought.pyface.workbench.api import Perspective, PerspectiveItem
from enthought.pyface.workbench.api import TraitsUIView
from enthought.traits.api import List

class LorenzPerspective(Perspective):
    """ A perspective containing the default analysis views. """
    
    name             = 'Lorenz'
    show_editor_area = False

    contents = [
        PerspectiveItem(id='lorenz.data'),
        PerspectiveItem(id='lorenz.plot2d')
    ]

class LorenzUIPlugin(Plugin):

    id = 'acme.lorenz.ui'
    name = 'Lorenz UI'

    # Extension points Ids.
    PERSPECTIVES   = 'enthought.envisage.ui.workbench.perspectives'
    VIEWS          = 'enthought.envisage.ui.workbench.views'
    perspectives   = List(contributes_to=PERSPECTIVES)
    views = List([], contributes_to=VIEWS)

    def _perspectives_default(self):
        return [LorenzPerspective]

    def _views_default(self):
        return [self._create_data_view, self._create_plot2d_view]

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_data_view(self, **traits):
        """ Factory method for the data view. """

        #from acme.lorenz.api import DataView, Lorenz
        #from cns.data.type import Animal
        #from cns.data.io import load_cohort
        from cns.data.ui.cohort import CohortView
        #fname = 'c:/users/brad/desktop/BNB/simple.cohort.hd5'
        #fname = '/home/bburan/projects/data/BNB_dt_group_6_CHL.cohort.hd5'
        #cohort = load_cohort(0, fname)
        #fd = FileDialog(action='open',
                        #default_directory='c:/users/brad/desktop/BNB',
                        #wildcard='*.cohort.hd5')
        #fd.open()
        #if fd.open() ==  OK and fd.path <> '':
            #cohort = load_cohort(0, fname)

        cohort = self.application.get_service('cns.data.type.Cohort')

        data_view = TraitsUIView(
            id   = 'lorenz.data',
            name = cohort.description,
            obj = CohortView(cohort=cohort),
            view = 'detailed_view',
            **traits
        )

        return data_view
    
    def _create_plot2d_view(self, **traits):
        """ Factory method for the plot2D view. """

        return self._create_data_view(**traits)

        from acme.lorenz.api import Lorenz, Plot2DView

        plot2d_view = TraitsUIView(
            id   = 'lorenz.plot2d',
            name = 'Plot 2D',
            obj  = Plot2DView(lorenz=self.application.get_service(Lorenz)),
            **traits
        )

        return plot2d_view
    
#### EOF ######################################################################
