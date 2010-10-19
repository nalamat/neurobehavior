def load_cohort_dialog(default_path='/home/bburan/projects/data'):
    from cns.data.io import load_cohort
    from cns.data.ui.cohort import CohortAnalysisView
    from enthought.pyface.api import FileDialog, OK

    fd = FileDialog(action='open',
                    default_directory=default_path,
                    wildcard='*.cohort.hd5')

    if fd.open() ==  OK and fd.path <> '':
        return load_cohort(0, fd.path)
    else:
        return None
