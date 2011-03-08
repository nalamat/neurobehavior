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

from enthought.traits.ui.extras.checkbox_column import CheckboxColumn
from cns.data.ui.cohort import SimpleAnimalAdapter

class ListColumn(ObjectColumn):
    
    format_func = Any

    def _format_func_default(self):
        return lambda x: ', '.join([('%.4f' % e).rstrip('0') for e in x])
    
    def cmp(self, object1, object2):
        return cmp(list(self.get_raw_value(object1)),
                   list(self.get_raw_value(object2)))

experiment_table = TableEditor(
    editable=False,
    filter_name='filter',
    selected='selected_experiment',
    dclick='dclicked_experiment',
    selection_mode='rows',
    columns=[CheckboxColumn(name='selected', label=''),
             ObjectColumn(name='date'),
             ObjectColumn(name='warn_trial_count', label='Trials'),
             ObjectColumn(name='duration', label="Dur"),
             ObjectColumn(name='water_infused', label="H2O", format='%.2f'),
             ListColumn(name='pars', label='Parameters'),
            ])

from cns.experiment.data.aversive_data import RawAversiveData
from cns.experiment.data.aversive_data import AnalyzedAversiveData
from cns.experiment.data.aversive_data import GrandAnalyzedAversiveData

from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView
from cns.experiment.data.aversive_data_view import SummaryAversiveDataView
from cns.experiment.data.experiment_data_view import AnalyzedView

class DataView(HasTraits):

    cohort = Instance('cns.data.type.Cohort')
    selected_animal = Instance('cns.data.type.Animal', ())
    selected_experiment = Instance(RawAversiveData, ())
    selected_experiment = List(Instance(RawAversiveData))
    dclicked_experiment = Event

    selected_experiment_view = Instance(AnalyzedView)

    def __init__(self, cohort, *args, **kw):
        super(DataView, self).__init__(cohort=cohort, *args, **kw)

    @on_trait_change('selected_animal.experiments.selected')
    def _selected_experiment_changed(self, new):
        #data = [AnalyzedAversiveData(data=d) for d in new]
        data = [AnalyzedAversiveData(data=d) for d in
                self.selected_animal.experiments if d.selected]
        analyzed = GrandAnalyzedAversiveData(data=data)
        view = SummaryAversiveDataView(analyzed=analyzed)
        self.selected_experiment_view = view

    #def _dclicked_experiment(self, info):
    #    data, object = info
    #    analyzed = AnalyzedAversiveData(data=data)
    #    view = AnalyzedAversiveDataView(analyzed=analyzed)
    #    result = view.edit_traits()
    #    #self.selected_experiment_view = view

    #filter = Property(depends_on='+filter')
    #min_trials = Int(5, filter=True)
    #min_water = Float(0.5, filter=True)

    traits_view = View(
        HSplit(
            VSplit(
                Item('object.cohort.animals{}', 
                     editor=TabularEditor(
                         adapter=SimpleAnimalAdapter(),
                         editable=False,
                         selected='selected_animal',
                         multi_select=False,
                         show_titles=False),
                    ),
                #VGroup('min_trials', 'min_water', label='Filters'),
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

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Experiment browser')
    parser.add_argument('file', type=str, nargs=1)
    op = parser.parse_args()
    try:
        from cns.data.io import load_cohort
        cohort = load_cohort(0, op.file[0])
    except:
        from cns.data.ui import load_cohort_dialog
        cohort = load_cohort_dialog()

    if cohort is not None:
        DataView(cohort).configure_traits()

if __name__ == '__main__':
    main()
