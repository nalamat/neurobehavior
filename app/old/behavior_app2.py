#------------------------------------------------------------------------------
# Copyright (c) 2005, Enthought, Inc.
# All rights reserved.
# 
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
# Thanks for using Enthought open source!
# 
# Author: Enthought, Inc.
# Description: <Enthought pyface package component>
#------------------------------------------------------------------------------
""" Application window example. """

# Important! Must be first import following any __future__ imports
import settings

from cns.data import io_gui

# Enthought library imports.
from enthought.pyface.api import ApplicationWindow, GUI
from enthought.pyface.action.api import Action, Group, MenuManager, MenuBarManager
#from enthought.traits.ui.menu import Action, Menu, MenuBar
from enthought.pyface.action.api import StatusBarManager, ToolBarManager
from enthought.pyface.api import information

class MainWindow(ApplicationWindow):

    pump_connected = False

    def __init__(self, **kw):
        super(MainWindow, self).__init__(**kw)
        self.connect()
        self.create_menu()

    def _exit_changed(self, event):
        print 'changed'

    def _exit_fired(self, event):
        print 'fired'

    def _on_exit(self, event):
        print 'exiting'
        information(self.control, 'exiting now')

    def connect(self):
        from cns import equipment
        self.equipment = equipment
        if self.equipment.pump_controller is not None:
            self.pump_connected = True

    def create_menu(self):
        actions = [Action(name='Load Cohort', 
                          on_perform=self.load_cohort,
                          id='load_cohort',
                          enabled=False), 
                   Action(name='Edit Cohort', 
                          on_perform=self.load_cohort,
                          enabled=True),
                   Action(name='Create Cohort', action='create_cohort'), ]

        animal_actions = Group(*actions, id='animal')

        enabled = 'handler.equipment.pump_controller is not None'
        actions = [Action(name='Calibrate', 
                          enabled=False),
                   Action(name='Load Calibration', 
                          enabled=False),
                   '-',
                   Action(name='Infuse pump', on_perform=self.pump_infuse,
                          enabled=self.pump_connected),
                   Action(name='Withdraw pump', on_perform=self.pump_withdraw,
                          enabled=False),
                   ]

        equipment_actions = actions

        actions = [Action(name='Select paradigm', action='load_paradigm'),
                   Action(name='Edit paradigm', action='edit_paradigm',
                          enabled_when='paradigm is not None'),
                   Action(name='Save paradigm', action='save_paradigm'),
                   Action(name='Create new paradigm', action='create_paradigm'),
                   '_',
                   Action(name='Run experiment', action='run_experiment'),]

        experiment_actions = actions

        animal_menu = MenuManager(animal_actions, name='&Animals')
        #equipment_menu = MenuManager(*equipment_actions, name='&Equipment')
        #experiment_menu = MenuManager(*experiment_actions, name='&Experiment')
        #menu = MenuBarManager(animal_menu, equipment_menu, experiment_menu)
        self.menu_bar_manager = MenuBarManager(animal_menu)
        #print menu

    def pump_infuse(self):
        print 'here'

    def pump_withdraw(self):
        print 'here'

    def load_cohort(self):
        self.cohort_path, self.cohort = io_gui.load_cohort()

if __name__ == '__main__':
    gui = GUI()
    window = MainWindow()
    window.open()
    gui.start_event_loop()
