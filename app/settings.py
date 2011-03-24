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
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'simple',
                },
            'file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'formatter': 'time',
                'filename': filename,
                }
            },
        'loggers': {
            'enthought.chaco.barplot': {
                'level': 'CRITICAL',
                },
            },
        'root': {
            'level': 'DEBUG',
            'handlers': ['console', 'file'],
            },
        }

logging.config.dictConfig(logging_config)
