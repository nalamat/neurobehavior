from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt4'
import  tables
from cns.data.h5_utils import iter_nodes, walk_nodes
from cns.data import persistence

from enthought.traits.api import *
from enthought.traits.ui.api import *

import logging
log = logging.getLogger()
log.setLevel(logging.ERROR)
log.addHandler(logging.StreamHandler())

from cns.data.type import Cohort, Animal
from cns.experiment.data.aversive_data import RawAversiveData, \
    AnalyzedAversiveData
from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView

from cns.data.ui.cohort import simple_cohort_table

def fmt_list(x):
    return ', '.join([('%.4f' % e).rstrip('0') for e in x])

from cns.data.ui.cohort import SimpleAnimalAdapter

class ListColumn(ObjectColumn):
    
    format_func = Any(fmt_list)
    
    def cmp(self, object1, object2):
        return cmp(list(self.get_raw_value(object1)),
                   list(self.get_raw_value(object2)))

experiment_table = TableEditor(
    editable=False,
    selected='selected_experiment',
    dclick='dclicked_experiment',
    columns=[ObjectColumn(name='date'),
             ObjectColumn(name='warn_trial_count', label='Trials'),
             ObjectColumn(name='duration', label="Dur"),
             ObjectColumn(name='water_infused', label="H2O", format='%.2f'),
             ListColumn(name='pars', label='Parameters'),
            ])

from cns.experiment.data.aversive_data import RawAversiveData
from cns.experiment.data.aversive_data import AnalyzedAversiveData
from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView

class DataView(HasTraits):

    cohort = Instance('cns.data.type.Cohort')
    selected_animal = Instance('cns.data.type.Animal', ())
    selected_experiment = Instance(RawAversiveData, ())
    dclicked_experiment = Event

    selected_experiment_view = Instance(AnalyzedAversiveDataView)

    def _selected_experiment_view_default(self):
        if self.selected_experiment is None:
            data = RawAversiveData()
        else:
            data = self.selected_experiment
        analyzed = AnalyzedAversiveData(data=data)
        view = AnalyzedAversiveDataView(analyzed=analyzed)
        return view

    @on_trait_change('dclicked_experiment')
    def _dclicked_experiment(self, info):
        data, object = info
        analyzed = AnalyzedAversiveData(data=data)
        view = AnalyzedAversiveDataView(analyzed=analyzed)
        self.selected_experiment_view = view

    #filter = Property(depends_on='+filter')
    #min_trials = Int(5, filter=True)
    #min_water = Float(0.5, filter=True)

    #def _get_filter(self):
    #    return lambda o: (o.total_trials >= self.min_trials) and \
    #                     (o.water_infused >= self.min_water)

    traits_view = View(
        HSplit(
            VSplit(
                Item('object.cohort.animals{}', editor=simple_cohort_table),
                Item('object.selected_animal.experiments{}',
                     editor=experiment_table),
            ),
            Item('selected_experiment_view{}',
                 editor=InstanceEditor(view='post_analysis_view'),
                 style='custom'),
        ),
        height=0.95,
        width=0.95,
        resizable=True)

def load_data(filename):
    from cns.data.io import load_cohort
    cohort = load_cohort(0, filename)
    #return cohort
    f = tables.openFile(filename, 'r')
    for animal in cohort.animals:
        node = f.getNode(animal.store_path)
        #experiments = iter_nodes(node.experiments, _v_name='aversive_date_')
        for node in iter_nodes(node.experiments, _v_name='aversive_date_'):
            try:
                data = persistence.load_object(node.Data)
                animal.experiments.append(data)
            except persistence.PersistenceReadError:
                pass
    return cohort

if __name__ == '__main__':
    #d.configure_traits()
    import argparse
    parser = argparse.ArgumentParser(description='Experiment browser')
    parser.add_argument('file', type=str, nargs=1)
    op = parser.parse_args()
    #browse_data(op.file[0])
    cohort = load_data(op.file[0])
    from cns.data.ui.cohort import CohortView
    #CohortView(cohort=cohort).configure_traits(view='simple_view')
    DataView(cohort=cohort).configure_traits()
