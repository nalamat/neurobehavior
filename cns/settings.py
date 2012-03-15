'''
Settings file

Variable names in capital letters indicate that this is a setting that can be
overridden in a custom settings.py file that NEUROBEHAVIOR_SETTINGS environment
variable points to.
'''

import os, re, logging
from os import path

# Ensure that ETS toolkit will default to PyQt4 and use the PyQt (instead of
# the less stable PySide backend) if we load it
os.environ['ETS_TOOLKIT'] = 'qt4' 
#os.environ['QT_API'] = 'pyqt'

# Maximum (safe) output voltage for DACs to speaker
MAX_SPEAKER_DAC_VOLTAGE = 7

# Recommended size (in bytes) to segment the raw physiology data into for
# loading into memory.  You can probably get away with bigger chunks for most of
# the data files; however, if a large number of artifacts are present (e.g. from
# the headstage falling off), these will trigger the event detection algorithm
# and cause memory size to balloon.
CHUNK_SIZE      = 50e6

# Size of sample (in seconds) to use for computing the noise floor
NOISE_DURATION  = 16 

try:
    BASE_DIRECTORY  = os.environ['NEUROBEHAVIOR_BASE']
except KeyError:
    import warnings
    import textwrap
    # Default to the user's home directory and raise a warning.
    BASE_DIRECTORY = path.expanduser('~')
    mesg = '''No NEUROBEHAVIOR_BASE environment variable defined.  Defaulting to
    the user's home directory, {}.  In the future, it is recommended that you
    create a base directory where the paradigm settings, calibration data, log
    files and data files can be stored.  Once this directory is created, create
    the environment variable, NEUROBEHAVIOR_BASE with the path to the directory
    as the value.'''
    warnings.warn(textwrap.dedent(mesg.format(BASE_DIRECTORY)))

LOG_ROOT        = path.join(BASE_DIRECTORY, 'logs')        # log files
TEMP_ROOT       = path.join(BASE_DIRECTORY, 'temp')        # temp files
DATA_ROOT       = path.join(BASE_DIRECTORY, 'data')        # data files
COHORT_ROOT     = DATA_ROOT                                # cohort files
CAL_ROOT        = path.join(BASE_DIRECTORY, 'calibration') # calibration files
SETTINGS_ROOT   = path.join(BASE_DIRECTORY, 'settings')
PARADIGM_ROOT   = path.join(SETTINGS_ROOT, 'paradigm')
PHYSIOLOGY_ROOT = path.join(SETTINGS_ROOT, 'physiology')

# Default filename extensions used by the FileBrowser dialog to open/save files.
COHORT_WILDCARD     = 'Cohort files (*.cohort.hd5)|*.cohort.hd5|'
PARADIGM_WILDCARD   = 'Paradigm settings (*.par)|*.par|'
PHYSIOLOGY_WILDCARD = 'Physiology settings (*.phy)|*.phy|'

# Be sure to update the RPvds circuit, physiology.rcx, with the appropriate
# snippet size for the SpikeSort component if this value is changed.
PHYSIOLOGY_SPIKE_SNIPPET_SIZE = 20

# __file__ is a special variable that is available in all Python files (when
# loaded by the Python interpreter) that contains the path of the current file
# or script. We extract the directory portion of the path and use that to
# determine where the RCX files are stored. We keep components in source code
# control as well to ensure that changes to the RCX files track changes to the
# software.
NEUROBEHAVIOR_BASE = path.abspath(path.join(path.dirname(__file__), '..'))

# Consider making these a list of lists.  That way we can specify a paradigms
# search path (e.g. users can store their paradigms in different locations and
# Neurobehavior will search for this).  This may be a bit dangerous as it
# increases the complexity of the program structure with little gain for
# end-users.
PARADIGMS_ROOT = path.join(NEUROBEHAVIOR_BASE, 'paradigms')
RCX_ROOT = path.join(NEUROBEHAVIOR_BASE, 'components')

def get_recent_cal(pattern):
    try:
        files = os.listdir(CAL_ROOT)
        files = [path.join(CAL_ROOT, f) for f in files if pattern.match(f)]
        files = [(path.getmtime(f), f) for f in files]
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


# By convention, settings are in all caps.  Print these to the log file to
# facilitate debugging other users' programs.
log = logging.getLogger()
for k, v in sorted(globals().items()):
    if k == k.upper():
        log.debug("CNS SETTING %s : %r", k, v)

# Color settings for the experiments
COLOR_NAMES = {
    'light green': '#98FB98',
    'dark green': '#2E8B57',
    'light red': '#FFC8CB',
    'dark red': '#FA8072',
    'gray': '#D3D3D3',
    'light blue': '#ADD8E6',
    'white': '#FFFFFF',
    }

EXPERIMENT_COLORS  = {
    'GO_REMIND': COLOR_NAMES['dark green'],
    'GO': COLOR_NAMES['light green'],
    'NOGO_REPEAT': COLOR_NAMES['dark red'],
    'NOGO': COLOR_NAMES['light red'],

    # In the first version of the appetitive trial log (and also possibly the
    # aversive) the GO_REMIND ttype was logged as REMIND.  This is left in for
    # backwards-compatibility when reviewing older experiments using the
    # review_physiology.py application.
    'REMIND': COLOR_NAMES['dark green'],
    }

PAIRED_COLORS_RGB_NORM = [
   (0.900, 0.100, 0.200),
   (1.000, 0.600, 0.750),
   (0.400, 0.300, 1.000),
   (0.800, 0.750, 1.000),
   (0.100, 0.700, 1.000),
   (0.650, 0.930, 1.000),
   (0.200, 1.000, 0.000),
   (0.700, 1.000, 0.550),
   (1.000, 1.000, 0.200),
   (1.000, 1.000, 0.600),
   (1.000, 0.500, 0.000),
   (1.000, 0.750, 0.500),
   ]

# Format to use when generating time strings (see time.strptime for
# documentation re the format specifiers to use below)
TIME_FORMAT = '%Y_%m_%d_%H_%M_%S'

# Wildcards to use when presenting a GUI prompt to open the relevant file
PHYSIOLOGY_RAW_WILDCARD = 'Raw (*_raw.hd5)|*_raw.hd5|'
PHYSIOLOGY_EXTRACTED_WILDCARD = 'Extracted (*_extracted*.hd5)|*_extracted*.hd5|'
PHYSIOLOGY_SORTED_WILDCARD = 'Sorted (*_sorted*.hd5)|*_sorted*.hd5|'
