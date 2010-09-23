from cns.data import persistence
from cns.experiment.data.aversive_data import AnalyzedAversiveData
from numpy import array
from cns.experiment.data import aversive_data, aversive_data_view
import tables
filename = 'c:/users/brad/desktop/BNB_dt_group_5_control.cohort.hd5'


f = tables.openFile(filename, 'r')
node = f.getNode('/Cohort_0/animals/Animal_0/experiments/aversive_date_2010_07_21_12_40_30')

