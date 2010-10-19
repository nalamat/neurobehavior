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
                                    ObjectColumn(name='water_infused',
                                                 format='%.2f'),
                                    ListColumn(name='pars'),
                                    ObjectColumn(name='warn_trial_count')])

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

def process_animal(animal):
    analyzed = []
    for experiment in animal.experiments:
        if experiment._v_name.startswith('aversive_date_'):
            try:
                data = persistence.load_object(experiment.Data)
                if filter(data):
                    analyzed.append(AnalyzedAversiveData(data=data))
            except persistence.PersistenceReadError:
                print 'Unable to parse ' + experiment._v_pathname
    return GrandAnalyzedAversiveData(data=analyzed)

def process_file(filename):
    fin = tables.openFile(filename, 'r')
    animals = []
    analyzed = []
    for node in fin.root.Cohort_0.animals:
        for experiment in node.experiments:
            #print experiment
            if experiment._v_name.startswith('aversive_date_'):
                print experiment._v_pathname
                try:
                    data = persistence.load_object(experiment.Data)
                    analyzed.append(AnalyzedAversiveData(data=data))
                except persistence.PersistenceReadError:
                    print 'Unable to parse ' + experiment._v_pathname
    return GrandAnalyzedAversiveData(data=analyzed)

def foo():
    import tables
    from cns.data import persistence
    f = tables.openFile('BNB_dt_group_5_control.cohort.hd5', 'r')
    data = persistence.load_object(f.root.Cohort_0.animals.Animal_0.experiments.aversive_date_2010_08_26_17_42_27.Data)
    data = persistence.load_object(f.root.Cohort_0.animals.Animal_0.experiments.aversive_date_2010_08_20_08_12_14.Data) 
    print data.warn_par_mask
    print data.par_warn_count
    print data.pars
    from cns.experiment.data.aversive_data import AnalyzedAversiveData
    print AnalyzedAversiveData(data=data).par_info
    return data

if __name__ == '__main__':
    foo()
    #import sys
    #ga = process_file(sys.argv[1])
    #print ga.par_info
