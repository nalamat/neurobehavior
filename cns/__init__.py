from os.path import dirname, join, abspath

LIBRARY_ROOT = dirname(abspath(__file__))
#DATA_ROOT = abspath(join(LIBRARY_ROOT, '../../data'))
DATA_ROOT = 'C:/experiments/data'
CONFIG_ROOT = abspath(join(LIBRARY_ROOT, '../config'))

PAR_WILDCARD    = 'Paradigm files (*.paradigm)|*.paradigm|'
PAR_PATH        = join(CONFIG_ROOT, 'paradigm')

#COHORT_WILDCARD = 'Cohort files (*.cohort)|*.cohort|'
COHORT_WILDCARD = 'Cohort files (*.cohort.hd5)|*.cohort.hd5|'
COHORT_PATH     = DATA_ROOT
