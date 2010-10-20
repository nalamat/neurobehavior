from enthought.envisage.api import Plugin, ServiceOffer
from enthought.traits.api import List

class AnimalPlugin(Plugin):

    id = 'cns.data.animal'
    name = 'Animal'

    service_offers = List(contributes_to='enthought.envisage.service_offers')

    def _service_offers_default(self):
        return [ServiceOffer(protocol='cns.data.type.Animal',
                             factory='cns.data.type.Animal')]
