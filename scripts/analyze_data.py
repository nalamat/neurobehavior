from cns.data import persistence
from cns.experiment.data.aversive_data import AnalyzedAversiveData
from numpy import array
from cns.util.math import d_prime
from cns.experiment.data import aversive_data, aversive_data_view
from cns.data import h5_utils
import tables
#node = f.getNode('/Cohort_0/animals/Animal_6/experiments/aversive_date_2010_08_17_17_06_16/')
#base = '/Cohort_0/animals/Animal_%d/'

import logging
logging.root.setLevel(logging.ERROR)

from enthought.traits.ui.tabular_adapter import TabularAdapter
from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.traits.ui.api import TabularEditor
from enthought.traits.ui.table_column import ObjectColumn
from enthought.traits.ui.table_filter import TableFilter

class ListColumn(ObjectColumn):
    
    format_func = Any(lambda x: ', '.join([str(e) for e in x]))
    
    def cmp(self, object1, object2):
        return cmp(list(self.get_raw_value(object1)),
                   list(self.get_raw_value(object2)))

experiment_table = TableEditor(editable=False,
                           filter_name='filter',
                           filtered_indices='filtered_experiments',
                           columns=[ObjectColumn(name='duration'),
                                    #ObjectColumn(name='date'),
                                    ObjectColumn(name='water_infused'),
                                    ListColumn(name='pars'),
                                    ObjectColumn(name='total_trials')])

analyzed_table = TableEditor(editable=False,
                            #filter_name='filter',
                            columns=[ListColumn(name='pars'),
                                     ListColumn(name='par_fa_frac')])

from cns.data.ui.cohort import simple_cohort_table

class ExperimentCollection(HasTraits):
    
    animals = List
    experiments = Property(List, depends_on='selected_animals')
    #analyzed = Property(List, depends_on='experiments')

    filter = Property(depends_on='+filter')
    filtered_experiments = List
    selected_animals = List
    
    # filters
    min_trials = Int(5, filter=True)
    min_water = Float(0.5, filter=True)
    
    num_experiments = Property(Int, depends_on='filtered_experiments')

    #def _get_analyzed(self):
    #    return [AnalyzedAversiveData(data=data) for data in self.experiments]

    def _get_num_experiments(self):
        return len(self.filtered_experiments)
    
    @cached_property
    def _get_experiments(self):
        if self.selected_animals:
            animals = self.animals[self.selected_animals]
        else:
            animals = self.animals
        experiments = []
        for animal in animals:
            experiments.extend(animal.experiments)
        return experiments
        
    def _get_filter(self):
        return lambda o: (o.total_trials >= self.min_trials) and \
                         (o.water_infused >= self.min_water)
    
    filter_view = VGroup('min_trials', 
                         'min_water', 
                         Item('num_experiments', 
                              label='Selected experiments',
                              style='readonly'),
                         label='Filters', 
                         show_border=True)

    traits_view = View(Tabbed(filter_view,
                              Item('animals',
                                   label='Animals',
                                   editor=simple_cohort_table),
                              Item('experiments',
                                   label='Experiments',
                                   editor=experiment_table),
                              Item('analyzed',
                                   label='Analyzed',
                                   editor=analyzed_table),
                              show_labels=False),
                       dock='horizontal',
                       resizable=True)

from cns.experiment.data.aversive_data import GrandAnalyzedAversiveData

filter = lambda o: o.total_trials >= 20

def process_file(filename, filter=None):
    fin = tables.openFile(filename, 'r')
    animals = []
    analyzed = []
    for node in fin.root.Cohort_0.animals:
        for experiment in node.experiments:
            print experiment
            if experiment._v_name.startswith('aversive_date_'):
                data = persistence.load_object(experiment.Data)
                if filter(data):
                    analyzed.append(AnalyzedAversiveData(data=data))
    return GrandAnalyzedAversiveData(data=analyzed)
            
if __name__ == '__main__':
    import sys
    lambda o: (o.total_trials >= 20) and \
              (o.water_infused >= 0.5)
    process_file(sys.argv[1])
