# Ensure that ETS toolkit will default to Qt4 if we load it
import os
os.environ['ETS_TOOLKIT'] = 'qt4' 

# Add the library folder for the branch
from os.path import abspath, dirname, join
import sys
libdir = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, libdir)

from cns import LOG_ROOT
import logging.config
from time import strftime

time_format = '[%(asctime)s] %(processName)s:%(threadName)s :: %(name)s - %(levelname)s - %(message)s'
simple_format = '%(name)s - %(levelname)s - %(message)s'
filename = join(LOG_ROOT, strftime('%Y%m%d_%H%M.log'))

logging_config = {
        'version': 1,
        'formatters': {
            'time': { 'format': time_format },
            'simple': { 'format': simple_format },
            },
        'handlers': {
            # This is what gets printed out to the console 
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'simple',
                },
            # This is what gets saved to the file
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'time',
                'filename': filename,
                }
            },
        # This is where you would change the logging level of specific modules.
        # This is very helpful when you are trying to debug a very specific
        # module and want to turn off the messages from other modules.
        'loggers': {
            # This module complains if you pass zero-length data to it for
            # plotting.  However, we initialize the plots with zero-length data
            # in the beginning of the experiment since we don't have any trials
            # yet.  Let's silence this module.
            'enthought.chaco.barplot': { 'level': 'CRITICAL', },
            # The debug level for this module is extremely noisy.
            'tdt.dsp_buffer': { 'level': 'INFO', },
            'tdt.dsp_circuit': { 'level': 'INFO', },
            'neurogen': { 'level': 'INFO', },
            },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            },
        }

logging.config.dictConfig(logging_config)
