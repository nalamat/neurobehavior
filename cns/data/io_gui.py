from . import io
import cns
from enthought.pyface.api import FileDialog, OK

def paradigm_save_prompt(self, info):
    if self.par_file == '':
        fd = FileDialog(action='save as',
                        default_directory=self.par_path,
                        wildcard=self.par_wildcard)
    else:
        fd = FileDialog(action='save as',
                        default_path=self.par_file,
                        wildcard=self.par_wildcard)

    # Confirms not to overwrite, so we don't have to do this
    if fd.open() == OK and fd.path <> '':
        if not fd.path.endswith('.paradigm'):
            fd.path += '.paradigm'
        self.par_file = fd.path
        with open(self.par_file, 'wb') as fh:
            pickle.dump(info.object.paradigm, fh, -1)

