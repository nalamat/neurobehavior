from enthought.traits.ui.menu import MenuBar, Menu, ActionGroup, Action
from enthought.traits.api import Str, File, Trait, Any
from enthought.traits.ui.api import Controller
from enthought.pyface.api import FileDialog, confirm, NO, error, OK, YES
import logging
import os
import sys
log = logging.getLogger(__name__)

def filehandler_menu():
    open_actions = [Action(name='New', action='new_file',
                           accelerator='Ctrl+N'),
                    Action(name='Load...', action='load_file',
                           accelerator='Ctrl+O')]

    save_actions = [Action(name='Save', action='save_file',
                           enabled_when='_modified', accelerator='Ctrl+S'),
                    Action(name='Save as...', action='saveas_file',
                           enabled_when='_modified')]

    open_actions = ActionGroup(*open_actions)
    save_actions = ActionGroup(*save_actions)
    menu = Menu(open_actions, save_actions, name='&File')
    return menu

def filehandler_menubar():
    return MenuBar(filehandler_menu())

def get_save_file(path, wildcard):
    wildcard = wildcard.split('|')[1][1:]
    fd = FileDialog(action='save as', default_directory=path, wildcard=wildcard)
    if fd.open() == OK and fd.path <> '':
        if not fd.path.endswith(wildcard):
            fd.path += wildcard
        return fd.path
    return None

def confirm_if_modified(func):
    '''Decorator for the filehandler class to ensure that changes are not
    discarded before the user has had a chance to save.
    '''
    def _inner(self, info, *args, **kw):
        if self.object_modified(info):
            mesg = 'This record has been modified. '
            mesg += 'Are you sure you wish to discard the changes?'
            if confirm(info.ui.control, mesg) == NO:
                return False
        return func(self, info, *args, **kw)
    return _inner

def check_valid(func):
    '''Decorator for the filehandler class to ensure that object is valid before
    it is saved.
    '''
    def _inner(self, info, *args, **kw):
        if not self.object_valid(info):
            mesg = 'Unable to save the data due to the following problem(s)\n'
            mesg += self.object_messages(info)
            error(info.ui.control, mesg)
            return False
        return func(self, info, *args, **kw)
    return _inner

class FileHandler(Controller):
    
    wildcard        = Str
    path            = File
    file            = Trait(None, File)
    modified_trait  = Trait(None, Str)
    
    def init(self, info):
        if self.modified_trait is not None:
            info.object.on_trait_change(self.update_title, 
                                        self.modified_trait)

    @confirm_if_modified
    def new_file(self, info):
        self.new_object(info)

    @confirm_if_modified
    def load_file(self, info):
        fd = FileDialog(action='open', 
                        default_directory=self.path,
                        wildcard=self.wildcard)
        if fd.open() == OK and fd.path <> '':
            log.debug('Loading %s', fd.path)
            try:
                self.load_object(info, fd.path)
                self.file = fd.path
                self.path = os.path.dirname(fd.path)
                info.ui.modified = True
                return True
            except Exception, e:
                log.exception(e)
                error(info.ui.control, str(e))
                raise
        else:
            return False
                
    @check_valid
    def save_file(self, info):
        if self.file is None:
            self.saveas_file(info)
        else:
            try:
                self.save_object(info, self.file)
            except BaseException, e:
                log.exception(e)
                mesg = 'There was an error saving the file.\n'
                mesg += str(e)
                error(info.ui.control, mesg)
                
    @check_valid
    def saveas_file(self, info):
        file = get_save_file(self.path, self.wildcard)
        if file is not None:
            try:
                self.save_object(info, file)
                self.file = file
                self.path = os.path.dirname(file)
            except BaseException, e:
                log.exception(e)
                error(info.ui.control, str(e))

    @confirm_if_modified
    def close(self, info, is_ok=True):
        return True

    def update_title(self, modified):
        if modified and not self.info.ui.title.endswith('*'):
            self.info.ui.title += '*'
        elif not modified and self.info.ui.title.endswith('*'):
            self.info.ui.title = self.info.ui.title.strip('*')

    # Method stubs for subclasses to override
    def load_object(self, info, file):
        raise NotImplementedError

    def save_object(self, info, file):
        raise NotImplementedError

    def object_valid(self, info):
        try: return info.object.is_valid()
        except: return True

    def object_messages(self, info):
        try: return info.object.err_messages()
        except: return True

    def object_modified(self, info):
        try: return info.object._modified
        except: return False
