# Ensure that ETS toolkit will default to Qt4 if we load it
import os, re
from os.path import dirname, join, abspath, getmtime

BASE_DIRECTORY  = 'E:/'
LOG_ROOT        = join(BASE_DIRECTORY, 'logs') # where log files should be stored
TEMP_ROOT       = join(BASE_DIRECTORY, 'temp') # location for temporary files
DATA_ROOT       = join(BASE_DIRECTORY, 'data') # location for data files
COHORT_ROOT     = DATA_ROOT                    # location for cohort files
CAL_ROOT        = join(BASE_DIRECTORY, 'calibration') # calibration files
RCX_ROOT        = join(abspath(dirname(__file__)), '../components')
COHORT_WILDCARD = 'Cohort files (*.cohort.hd5)|*.cohort.hd5|'

def get_recent_cal(pattern):
    try:
        files = os.listdir(CAL_ROOT)
        files = [join(CAL_ROOT, f) for f in files if pattern.match(f)]
        files = [(getmtime(f), f) for f in files]
        files.sort()
        files = [f[1] for f in files]
        return files[-1]
    except Exception, e:
        return None

# Find the most recent calibration files.  The assumption is that the files are
# intelligently named.
CAL_PRIMARY     = get_recent_cal(re.compile('.*primary.*'))
CAL_SECONDARY   = get_recent_cal(re.compile('.*secondary.*'))

# Device configuration
TDT_AUDIO = 'RZ6'
TDT_BEHAVIOR = 'RZ6'
TDT_PHYSIOLOGY = 'RZ5'

# Subprocess configuration
RCX_USE_SUBPROCESS      = False # Run IO as a subprocess?
RCX_PROCESS_POLL_PERIOD = 0.1   # Poll period in seconds
RCX_PROCESS_CACHE_SIZE  = 30    # Cache size in seconds for each buffer

# Options for pump syringe
SYRINGE_DEFAULT = 'Popper 20cc (glass)'
SYRINGE_DATA = {
        'B-D 10cc (plastic)'    : 14.43,
        'B-D 20cc (plastic)'    : 19.05,
        'B-D 30cc (plastic)'    : 21.59,
        'B-D 60cc (plastic)'    : 26.59,
        'Popper 20cc (glass)'   : 19.58,
        'B-D 10cc (glass)'      : 14.20,
        }

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
