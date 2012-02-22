from enthought.traits.ui.menu import MenuBar, Menu, ActionGroup, Action

def create_menubar():
    paradigm_actions = ActionGroup(
            Action(name='Load paradigm', action='load_paradigm'),
            Action(name='Save paradigm as', action='saveas_paradigm'),
            #Action(name='Select parameters', action='select_parameters'),
            )
    calibration_actions = ActionGroup(
            #Action(name='Load calibration', action='load_calibration'),
            Action(name='Show calibration', action='show_calibration'),
            Action(name='Show signal', action='show_signal'),
            )
    paradigm_menu = Menu(paradigm_actions, name='&Paradigm')
    calibration_menu = Menu(calibration_actions, name='&Calibration')
    return MenuBar(paradigm_menu, calibration_menu)
