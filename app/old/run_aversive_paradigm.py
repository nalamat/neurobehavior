import settings

from cns.experiment.controller import AversiveController
from cns.experiment.data import AnalyzedAversiveDataView, AversiveData
from cns.experiment.paradigm import AversiveParadigmView, AversiveParadigm
from enthought.traits.api import HasTraits, Instance, DelegatesTo, Any, \
    on_trait_change, Bool
from enthought.traits.ui.api import View, HGroup, Item, VGroup, InstanceEditor

if __name__ == '__main__':
    import tables
    import os
    fh = tables.openFile('test.h5', 'w')
   
    paradigm = AversiveParadigm()
    paradigm.signal_warn.variables = ['frequency']
    paradigm.par_remind = 1000
    model = AversiveExperiment(store_node=fh.root, paradigm=paradigm)
    handler = AversiveController()
    model.configure_traits(handler=handler)
