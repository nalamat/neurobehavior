'''
Created on May 5, 2010

@author: Brad
'''
from cns.experiment.data import AversiveData
from cns.experiment.data import AnalyzedAversiveDataView
import tables

if __name__ == '__main__':
    store = tables.openFile('test.h5', 'w')
    #ae = AversiveExperiment(store_node=store.root)
    #ae.paradigm.signal_warn.variables = ['frequency']
    #handler = AversiveController()
    #ae.configure_traits(handler=handler)
    data = AversiveData(store_node=store.root)
    AnalyzedAversiveDataView(data=data).configure_traits()