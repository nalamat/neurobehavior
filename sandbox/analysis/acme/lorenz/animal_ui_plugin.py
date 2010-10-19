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


class AnimalUIPlugin(Plugin):
    """
    """

    # Extension points Ids.
    PERSPECTIVES   = 'enthought.envisage.ui.workbench.perspectives'
    VIEWS          = 'enthought.envisage.ui.workbench.views'

    #### 'IPlugin' interface ##################################################

    # The plugin's unique identifier.
    id = 'cns.data.type.Animal'

    # The plugin's name (suitable for displaying to the user).
    name = 'Animal Edit'

    #### Contributions to extension points made by this plugin ################

    # Perspectives.
    perspectives = List(contributes_to=PERSPECTIVES)

    def _perspectives_default(self):
        """ Trait initializer. """

        return [LorenzPerspective]

    # Views.
    views = List(contributes_to=VIEWS)

    def _views_default(self):
        """ Trait initializer. """
        return [self._create_data_view, self._create_plot2d_view]

    ###########################################################################
    # Private interface.
    ###########################################################################

    def _create_data_view(self, **traits):
        """ Factory method for the data view. """

        #from acme.lorenz.api import DataView, Lorenz
        from cns.data.type import Animal
        from cns.data.ui.cohort import CohortView

        data_view = TraitsUIView(
            id   = 'lorenz.data',
            name = 'Data',
            #obj  = DataView(lorenz=self.application.get_service(Lorenz)),
            obj  = CohortView(cohort=self.application.get_services(Cohort)[-1]),
            **traits
        )

        return data_view
    
    #def _create_plot2d_view(self, **traits):
    #    """ Factory method for the plot2D view. """

    #    from acme.lorenz.api import Lorenz, Plot2DView

    #    plot2d_view = TraitsUIView(
    #        id   = 'lorenz.plot2d',
    #        name = 'Plot 2D',
    #        obj  = Plot2DView(lorenz=self.application.get_service(Lorenz)),
    #        **traits
    #    )

    #    return plot2d_view
    
#### EOF ######################################################################
