#import os
#import settings
from enthought.pyface.api import ApplicationWindow, GUI
from enthought.pyface.action.api import MenuBarManager, MenuManager, Action

#from run_aversive_paradigm import AversiveExperiment
#from cns.experiment.controller import AversiveController
#import tables
#from cns import data
#from cns.data.type import Cohort
#from cns.data.view.edit_cohort import CohortView, CohortEditView
#from cns.equipment.pump import Pump
#from cns.experiment.data import AversiveData, AnalyzedAversiveData, \
#    AnalyzedAversiveDataView, AnalyzedView, ExperimentData
#from cns.experiment.paradigm import AversiveParadigm, ParadigmView, \
#    AversiveParadigmView, Paradigm
#from cns.experiment.paradigm.aversive_paradigm_view import readonly_aversive_paradigm_view
#from enthought.pyface.api import FileDialog, OK, error
#from enthought.traits.api import File, DelegatesTo, HasTraits, Instance, \
#    Property, Str, on_trait_change, Any, Button, Bool, Event
#from enthought.traits.ui.api import Handler, View, Item, HGroup, VGroup, spring, \
#    InstanceEditor
#from enthought.traits.ui.menu import Action, Menu, MenuBar
#import cPickle as pickle
#import cns

class MainWindow(ApplicationWindow):

    #par_wildcard    = cns.PAR_WILDCARD
    #par_path        = cns.PAR_PATH
    #par_file        = File

    #cohort_wildcard = cns.COHORT_WILDCARD
    #cohort_path     = cns.COHORT_PATH
    #cohort_file     = File

    #equipment       = Any

    def __init__(self, **kw):
        super(MainWindow, self).__init__(**kw)
        #self.create_menu()

    '''
    def create_menu(self):
        actions = [Action(name='Load Cohort', action='load_cohort'), 
                   Action(name='Edit Cohort', action='edit_cohort',
                          enabled_when='cohort_loaded'),
                   Action(name='Create Cohort', action='create_cohort'), ]

        animal_actions = actions

        enabled = 'handler.equipment.pump_controller is not None'
        actions = [Action(name='Calibrate', action='calibrate',
                          enabled_when='False'),
                   Action(name='Load Calibration', action='load_cal',
                          enabled_when='False'),
                   '-',
                   Action(name='Infuse pump', action='pump_infuse',
                          enabled_when=enabled),
                   Action(name='Withdraw pump', action='pump_withdraw',
                          enabled_when=enabled),]

        equipment_actions = actions

        actions = [Action(name='Select paradigm', action='load_paradigm'),
                   Action(name='Edit paradigm', action='edit_paradigm',
                          enabled_when='paradigm is not None'),
                   Action(name='Save paradigm', action='save_paradigm'),
                   Action(name='Create new paradigm', action='create_paradigm'),
                   '_',
                   Action(name='Run experiment', action='run_experiment'),]

        experiment_actions = actions

        animal_menu = Menu(*animal_actions, name='&Animals')
        equipment_menu = Menu(*equipment_actions, name='&Equipment')
        experiment_menu = Menu(*experiment_actions, name='&Experiment')
        menu = MenuBar(animal_menu, equipment_menu, experiment_menu)
        self.menu_bar_manager = MenuBarManager(menu)
    '''
        
if __name__ == '__main__':
    #MainWindow().configure_traits()
    gui = GUI()
    print 'here'
    window = MainWindow()
    print 'here'
    window.open()
    print 'here'
    gui.start_event_loop()
