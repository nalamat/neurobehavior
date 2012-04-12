from cns.experiment.paradigm import AversiveParadigm
from cns.widgets.handler import FileHandler, filehandler_menubar
from traits.api import Instance, HasTraits, Bool, on_trait_change
from traitsui.api import View, Item, InstanceEditor
import cns
import pickle
import settings

class ParadigmFileHandler(FileHandler):

    path            = cns.PAR_PATH
    wildcard        = cns.PAR_WILDCARD
    modified_trait  = '_modified'

    def load_object(self, info, file):
        with open(file, 'rb') as fh:
            info.object.paradigm = pickle.load(fh)
        info.object._modified = False

    def save_object(self, info, file):
        with open(file, 'wb') as fh:
            pickle.dump(info.object.paradigm, fh, -1)
        info.object._modified = False

    def object_valid(self, info):
        return info.object.paradigm.is_valid()

    def object_messages(self, info):
        return info.object.paradigm.err_messages()

    def new_object(self, info):
        info.object.paradigm = AversiveParadigm()

class MainWindow(HasTraits):

    paradigm      = Instance(AversiveParadigm, ())
    _modified     = Bool(False)

    @on_trait_change('paradigm.+,'
                     'paradigm.signal_safe.+',
                     'paradigm.signal_warn.+',
                     'paradigm.shock_settings.+')
    def modified(self):
        self._modified = True

    def trait_view(self, parent=None):
        return View(Item('paradigm', style='custom',
                         #editor=InstanceEditor(view=aversive_view),
                         editor=InstanceEditor(view='edit_view'),
                         show_label=False),
                    resizable=True,
                    menubar=filehandler_menubar(),
                    handler=ParadigmFileHandler(),
                    title='Aversive Paradigm Editor',
                    )

if __name__ == '__main__':
    MainWindow().configure_traits()
