import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

def load_settings():
    # Load the default settings
    from os import environ
    from . import settings
    
    try:
        # Load the computer-specific settings
        path = environ['NEUROBEHAVIOR_SETTINGS']
        import imp
        from os.path import dirname
        extra_settings = imp.load_module('settings', open(path), dirname(path),
                                         ('.py', 'r', imp.PY_SOURCE))
        # Update the setting defaults with the computer-specific settings
        for setting in dir(extra_settings):
            value = getattr(extra_settings, setting)
            setattr(settings, setting, value)
    except KeyError:
        log.debug('No NEUROBEHAVIOR_SETTINGS defined')
    return settings
        
_settings = load_settings()

def set_config(setting, value):
    setattr(_settings, setting, value)
    
def get_config(setting):
    return getattr(_settings, setting) 
