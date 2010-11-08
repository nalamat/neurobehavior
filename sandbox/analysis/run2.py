from enthought.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt4'

import logging
log = logging.getLogger()
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

from enthought.envisage.ui.workbench.api import WorkbenchApplication
from enthought.envisage.api import Plugin, ServiceOffer
from enthought.envisage.ui.action.api import Action, Group
from enthought.envisage.ui.workbench.api import WorkbenchActionSet
from enthought.pyface.action.api import Action as ActionClass

#experiment_table = TableEditor(editable=False,
#                           filter_name='filter',
#                           filtered_indices='filtered_experiments',
#                           columns=[ObjectColumn(name='duration'),
#                                    #ObjectColumn(name='date'),
#                                    ObjectColumn(name='water_infused',
#                                                 format='%.2f'),
#                                    ListColumn(name='pars'),
#                                    ObjectColumn(name='warn_trial_count')])

class LoadCohortAction(ActionClass):

    name = 'Load Cohort'

    def perform(self, event):
        from cns.data.io import load_cohort
        from cns.data.ui.cohort import CohortAnalysisView
        from enthought.pyface.api import FileDialog, OK, information
        from enthought.pyface.workbench.api import TraitsUIView

        fd = FileDialog(action='open',
                        default_directory='/home/bburan/projects/data',
                        wildcard='*.cohort.hd5')

        if fd.open() ==  OK and fd.path <> '':
            if self.window.get_view_by_id(fd.path) is not None:
                information(None, "Cohort is already loaded")
            else:
                cohort = load_cohort(0, fd.path)
                for animal in cohort.animals:
                    print animal.experiments
                view = CohortAnalysisView(cohort=cohort)
                selected_view = TraitsUIView(id=fd.path,
                                             name=cohort.description,
                                             obj=view,
                                             view='simple_view')
                self.window.add_view(selected_view)

class CohortActionSet(WorkbenchActionSet):

    groups =  [Group(id="Cohort", path="MenuBar/File")]
    actions = [Action(path="MenuBar/File", group="Cohort",
                      class_name="__main__:LoadCohortAction")]

class CohortPlugin(Plugin):

    from enthought.traits.api import List

    id = 'plugins.Cohort'
    name = 'Cohort'

    ACTION_SETS = 'enthought.envisage.ui.workbench.action_sets'
    action_sets = List([CohortActionSet], contributes_to=ACTION_SETS)

class AnalysisApplication(WorkbenchApplication):

    id   = 'analysis'
    name = 'Data Analysis'

if __name__ == '__main__':
    from enthought.envisage.core_plugin import CorePlugin
    from enthought.envisage.ui.workbench.workbench_plugin import WorkbenchPlugin
    plugins = [
        CorePlugin(), 
        WorkbenchPlugin(), 
        CohortPlugin(), 
        ]
    AnalysisApplication(plugins=plugins).run()
