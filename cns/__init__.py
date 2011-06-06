import os
from os.path import dirname, join, abspath

BASE_DIRECTORIES = {
        'REGINA'        : 'E:/',            # In 1016
        'PC'            : 'F:/',            # In 1012
        'SEMPLE'        : None,             # Placeholder for Mal's computer
        'ROSENLAB'      : 'C:/EXPERIMENTS', # Merri's NEOUCOM computer
        'PHOENIX-NYU'   : 'C:/users/brad/workspace/neurobehavior_base',
        }

BASE_DIRECTORY = BASE_DIRECTORIES[os.getenv('COMPUTERNAME')]
LOG_ROOT    = join(BASE_DIRECTORY, 'logs') # where log files should be stored
TEMP_ROOT   = join(BASE_DIRECTORY, 'temp') # location for temporary files
DATA_ROOT   = join(BASE_DIRECTORY, 'data') # location for data files
COHORT_ROOT = DATA_ROOT                    # location for cohort files

# __file__ is a special variable that is available in all Python files (when
# loaded by the Python interpreter) that contains the file path.  We extract the
# directory portion of the path and use that to determine where the RCX files
# are stored.  We keep components in source code control as well to ensure that
# changes to the RCX files track changes to the software.
RCX_ROOT = join(abspath(dirname(__file__)), '../components')
TDT_AUDIO = 'RZ6'
TDT_BEHAVIOR = 'RZ6'
TDT_PHYSIOLOGY = 'RZ5'

RCX_USE_SUBPROCESS      = False # Run IO as a subprocess?
RCX_PROCESS_POLL_PERIOD = 0.1   # Poll period in seconds
RCX_PROCESS_CACHE_SIZE  = 30    # Cache size in seconds for each buffer

# extension to use for cohort files
COHORT_WILDCARD = 'Cohort files (*.cohort.hd5)|*.cohort.hd5|'

# Syringe data for the pump
SYRINGE_DEFAULT = 'Popper 20cc (glass)'
SYRINGE_DATA = {
        'B-D 10cc (plastic)'    : 14.43,
        'B-D 20cc (plastic)'    : 19.05,
        'B-D 30cc (plastic)'    : 21.59,
        'B-D 60cc (plastic)'    : 26.59,
        'Popper 20cc (glass)'   : 19.58,
        'B-D 10cc (glass)'      : 14.20,
        }

PHYSIOLOGY_CHANNELS = 16

if __name__ == '__main__':
    from os import makedirs
    for path in (DATA_ROOT, TEMP_ROOT, LOG_ROOT):
        try:
            makedirs(path)
        except OSError:
            print "Unable to make directory %s, check to see if it exists" % \
                  path
