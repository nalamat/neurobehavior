'''
Settings file

Variable names in capital letters indicate that this is a setting that can be
overridden in a custom settings.py file that NEUROBEHAVIOR_SETTINGS environment
variable points to.
'''

import os, re, logging
from os.path import dirname, join, abspath, getmtime

# Maximum (safe) output voltage for DACs to speaker
MAX_SPEAKER_DAC_VOLTAGE = 7

# Recommended size (in bytes) to segment the raw physiology data into for
# loading into memory.
CHUNK_SIZE      = 10e7

# Size of sample (in seconds) to use for computing the noise floor
NOISE_DURATION  = 16 

BASE_DIRECTORY  = os.environ['NEUROBEHAVIOR_BASE']
LOG_ROOT        = join(BASE_DIRECTORY, 'logs')        # log files
TEMP_ROOT       = join(BASE_DIRECTORY, 'temp')        # temp files
DATA_ROOT       = join(BASE_DIRECTORY, 'data')        # data files
COHORT_ROOT     = DATA_ROOT                           # cohort files
CAL_ROOT        = join(BASE_DIRECTORY, 'calibration') # calibration files
SETTINGS_ROOT   = join(BASE_DIRECTORY, 'settings')
PARADIGM_ROOT   = join(SETTINGS_ROOT, 'paradigm')
PHYSIOLOGY_ROOT = join(SETTINGS_ROOT, 'physiology')

# Default filename extensions used by the FileBrowser dialog to open/save files.
COHORT_WILDCARD     = 'Cohort files (*.cohort.hd5)|*.cohort.hd5|'
PARADIGM_WILDCARD   = 'Paradigm settings (*.par)|*.par|'
PHYSIOLOGY_WILDCARD = 'Physiology settings (*.phy)|*.phy|'

PROGRAM_BASE = abspath(join(dirname(__file__), '..'))
EXPERIMENT_ROOT = join(PROGRAM_BASE, 'launchers')
EXPERIMENT_PATTERN = join(EXPERIMENT_ROOT, '*.py')

def get_recent_cal(pattern):
    try:
        files = os.listdir(CAL_ROOT)
        files = [join(CAL_ROOT, f) for f in files if pattern.match(f)]
        files = [(getmtime(f), f) for f in files]
        files.sort()
        files = [f[1] for f in files]
        return files[-1]
    except Exception:
        return None

# We prefer that the calibration file name be in the format
# YYMMDD_descriptor_speaker.  For example:
# - 110627_1017_TDT_tweeter_primary
# - 110627_1017_Madisound_XOver_secondary
# - 110627_1012_Vifa_tweeter_primary
cal_primary_pattern = re.compile('\d{6}_[\w\d]+_primary.mat')
cal_secondary_pattern = re.compile('\d{6}_[\w\d]+_secondary.mat')

# Find the most recent calibration files.  The assumption is that the files are
# intelligently named.
CAL_PRIMARY     = get_recent_cal(cal_primary_pattern)
CAL_SECONDARY   = get_recent_cal(cal_secondary_pattern)

# Physiology settings
PHYSIOLOGY_CHANNELS = 16

# Chaco options
CHACO_NOAXES_PADDING = 5
CHACO_AXES_PADDING = [50, 5, 5, 50]

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

# __file__ is a special variable that is available in all Python files (when
# loaded by the Python interpreter) that contains the path of the current file
# or script. We extract the directory portion of the path and use that to
# determine where the RCX files are stored. We keep components in source code
# control as well to ensure that changes to the RCX files track changes to the
# software.
RCX_ROOT = join(abspath(dirname(__file__)), '../components')

# Ensure that ETS toolkit will default to PyQt4 and use the PyQt (instead of
# the less stable PySide backend) if we load it
os.environ['ETS_TOOLKIT'] = 'qt4' 
os.environ['QT_API'] = 'pyqt'

# By convention, settings are in all caps.  Print these to the log file to
# facilitate debugging other users' programs.
#log = logging.getLogger(__name__)
log = logging.getLogger()
for k, v in sorted(globals().items()):
    if k == k.upper():
        log.debug("CNS SETTING %s : %r", k, v)
