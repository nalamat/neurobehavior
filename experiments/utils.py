from enthought.pyface.api import FileDialog, OK
#import cPickle as pickle
import pickle

def get_save_file(path, wildcard):
    wildcard_base = wildcard.split('|')[1][1:]
    fd = FileDialog(action='save as', default_directory=path, wildcard=wildcard)
    if fd.open() == OK and fd.path <> '':
        if not fd.path.endswith(wildcard_base):
            fd.path += wildcard_base
        return fd.path
    return None

def load_instance(path, wildcard):
    fd = FileDialog(action='open', default_directory=path, wildcard=wildcard)
    if fd.open() == OK and fd.path <> '':
        with open(fd.path, 'rb') as infile:
            return pickle.load(infile)
    else:
        return None

def dump_instance(instance, path, wildcard):
    filename = get_save_file(path, wildcard)
    if filename is not None:
        with open(filename, 'wb') as outfile:
            pickle.dump(instance, outfile)
        return True
    return False
