from os import environ
from os.path import dirname
import imp

def load_settings():
    path = environ['NEUROBEHAVIOR_SETTINGS']
    return imp.load_module('settings', open(path), dirname(path), 
                           ('.py', 'r', imp.PY_SOURCE))
_settings = load_settings()

def set_config(setting, value):
    setattr(_settings, setting, value)
    
def get_config(setting):
    return getattr(_settings, setting)        

# __file__ is a special variable that is available in all Python files (when
# loaded by the Python interpreter) that contains the path of the current file
# or script. We extract the directory portion of the path and use that to
# determine where the RCX files are stored. We keep components in source code
# control as well to ensure that changes to the RCX files track changes to the
# software.
from os.path import join, abspath, dirname
set_config('RCX_ROOT', join(abspath(dirname(__file__)), '../components'))