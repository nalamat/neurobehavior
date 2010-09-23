from os.path import abspath, dirname, join
import sys
import tables
from cns.data import persistence

libdir = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, libdir)

filename = 'BNB_dt_group_5_control.cohort.hd5'
pathname = '/Cohort_0/animals/Animal_0/experiments/aversive_date_2010_07_19_11_23_39/Data'
f = tables.openFile(filename)
persistence.load_object(f, pathname)
