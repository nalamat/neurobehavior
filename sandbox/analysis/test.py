from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt4'

from enthought.pyface.workbench.api import TraitsUIView
from enthought.pyface.workbench.api import Workbench, WorkbenchWindow
from enthought.pyface.api import GUI

class AnalysisWindow(WorkbenchWindow):

    def _menu_bar_manager_default(self):
        from enthought.pyface.action.api import Action, MenuManager
        from enthought.pyface.workbench.action.api import MenuBarManager
        file_menu = MenuManager(
            Action(name='&Load Cohort', on_perform=self._load_cohort),
            Action(name='E&xit', on_perform=self.workbench.exit),
            Action(name='Views', on_perform=self._print_views),
            name='&File',
            id='FileMenu')
        return MenuBarManager(file_menu, window=self)

    def _print_views(self):
        for view in self.views:
            self.show_view(view)

    def _load_cohort(self):
        from cns.data.io import load_cohort
        from cns.data.ui.cohort import CohortAnalysisView
        from enthought.pyface.api import FileDialog, OK

        fd = FileDialog(action='open',
                        default_directory='/home/bburan/projects/data',
                        wildcard='*.cohort.hd5')

        if fd.open() ==  OK and fd.path <> '':
            if self.get_view_by_id(fd.path) is not None:
                return
            cohort = load_cohort(0, fd.path)
            view = CohortAnalysisView(cohort=cohort)
            selected_view = TraitsUIView(id='seleted item',
                                         name=cohort.description,
                                         obj=view,
                                         view='simple_view')
            self.add_view(selected_view)

def main(argv):

    gui = GUI()
    workbench = Workbench(state_location=gui.state_location,
                          window_factory=AnalysisWindow)
    window = workbench.create_window()
    window.open()

    gui.start_event_loop()

if __name__ == "__main__":
    import sys
    main(sys.argv)
