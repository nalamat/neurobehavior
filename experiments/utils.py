from enthought.pyface.api import FileDialog, OK
import cPickle as pickle

def get_save_file(path, wildcard):
    wildcard = wildcard.split('|')[1][1:]
    fd = FileDialog(action='save as', default_directory=path, wildcard=wildcard)
    if fd.open() == OK and fd.path <> '':
        if not fd.path.endswith(wildcard):
            fd.path += wildcard
        return fd.path
    return None

def load_instance(path, wildcard):
    fd = FileDialog(action='open', default_directory=path, wildcard=wildcard)
    if fd.open() == OK and fd.path <> '':
        import cPickle as pickle
        with open(fd.path, 'rb') as infile:
            return pickle.load(infile)
    else:
        return None

def dump_instance(instance, path, wildcard):
    filename = get_save_file(path, wildcard)
    if filename is not None:
        import cPickle as pickle
        with open(filename, 'wb') as outfile:
            pickle.dump(instance, outfile)
        return True
    return False

