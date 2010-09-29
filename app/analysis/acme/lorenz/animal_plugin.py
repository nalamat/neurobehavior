from enthought.envisage.api import Plugin, ServiceOffer
from enthought.traits.api import List

class AnimalPlugin(Plugin):
    """ 
    """

    # Extension points Ids.
    SERVICE_OFFERS = 'enthought.envisage.service_offers'

    # The plugin's unique identifier.
    id = 'cns.data.animal'

    # The plugin's name (suitable for displaying to the user).
    name = 'Animal'

    # Service offers.
    service_offers = List(contributes_to=SERVICE_OFFERS)

    def _service_offers_default(self):
        """ Trait initializer. """

        lorenz_service_offer = ServiceOffer(
            protocol = 'cns.data.type.Animal',
            factory = 'cns.data.type.Animal'
            #protocol = 'acme.lorenz.lorenz.Lorenz',
            #factory  = 'acme.lorenz.lorenz.Lorenz'
        )

        return [lorenz_service_offer]
    
#### EOF ######################################################################
