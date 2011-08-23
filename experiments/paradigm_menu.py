from enthought.traits.ui.menu import MenuBar, Menu, ActionGroup, Action

def create_menubar():
    actions = ActionGroup(
            Action(name='Load paradigm', action='load_paradigm'),
            Action(name='Save paradigm as', action='saveas_paradigm'),
            Action(name='Select parameters', action='select_parameters'),
            )
    menu = Menu(actions, name='&File')
    return MenuBar(menu)
