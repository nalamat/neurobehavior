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
logging.root.setLevel(logging.WARN)

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

from cns.data.ui.cohort import simple_cohort_table

class ExperimentCollection(HasTraits):
    
    animals = List
    experiments = Property(List, depends_on='selected_animals')
    filter = Property(depends_on='+filter')
    filtered_experiments = List
    selected_animals = List
    
    # filters
    min_trials = Int(5, filter=True)
    min_water = Float(0.5, filter=True)
    
    num_experiments = Property(Int, depends_on='filtered_experiments')
    
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
                              show_labels=False),
                       dock='horizontal',
                       resizable=True)

def process_file(filename):
    fin = tables.openFile(filename)
    animals = []
    for node in fin.walkNodes():
        if 'Animal' in node._v_name:
            animal = persistence.load_object(node)
            animal.experiments = []
            animals.append(animal)
            for subnode in node._f_walkNodes():
                if 'aversive' in subnode._v_name:
                    experiment = persistence.load_object(subnode.Data)
                    animal.experiments.append(experiment)
    ExperimentCollection(animals=animals).configure_traits()
            
def process_node(node, summary):
    #par_info = node.Data.Analyzed.AnalyzedAversiveData_0.par_info[:]
    data = persistence.load_object(node.Data)
    analyzed = AnalyzedAversiveData(data=data)
    par_info = analyzed.par_info
    paradigm = persistence.load_object(node.Paradigm)
    if analyzed.data.total_trials < 20:
        return summary
    if paradigm.signal_warn.variable == 'ramp_duration':
        dB = 97-paradigm.signal_warn.attenuation
        for row in par_info:
            key = row[0], dB
            append = row[1:5]
            summary[key] = summary.get(key, array([0, 0, 0, 0])) + append
    elif paradigm.signal_warn.variable == 'attenuation':
         dur = paradigm.signal_warn.ramp_duration
         for row in par_info:
            key = dur, 97-row[0]
            append = row[1:5]
            summary[key] = summary.get(key, array([0, 0, 0, 0])) + append
    return summary

def process_node(node, summary):
    #par_info = node.Data.Analyzed.AnalyzedAversiveData_0.par_info[:]
    data = persistence.load_object(node.Data)
    analyzed = AnalyzedAversiveData(data=data)
    par_info = analyzed.par_info
    paradigm = persistence.load_object(node.Paradigm)
    if analyzed.data.total_trials < 20:
        return summary
    if paradigm.signal_warn.variable == 'ramp_duration':
        dB = 97-paradigm.signal_warn.attenuation
        for row in par_info:
            key = row[0], dB
            append = row[1:5]
            summary[key] = summary.get(key, array([0, 0, 0, 0])) + append
    elif paradigm.signal_warn.variable == 'attenuation':
         dur = paradigm.signal_warn.ramp_duration
         for row in par_info:
            key = dur, 97-row[0]
            append = row[1:5]
            summary[key] = summary.get(key, array([0, 0, 0, 0])) + append
    return summary

if __name__ == '__main__':
    #filename = 'c:/users/brad/desktop/BNB_dt_group_5_control.cohort.hd5'
    filename = '/home/brad/projects/data/BNB_dt_group_5_control.cohort.hd5'
    #f = tables.openFile(filename, 'r')
    #process_animal(f.root.Cohort_0.animals.Animal_0)
