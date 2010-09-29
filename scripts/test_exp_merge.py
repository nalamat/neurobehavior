from os.path import abspath, dirname, join
import sys
import tables
from cns.data import persistence

libdir = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, libdir)

filename = 'c:/users/brad/desktop/BNB/BNB_dt_group_6_CHL.cohort.hd5'
base = '/Cohort_0/animals/Animal_3/experiments/'
pathname1 = base + 'aversive_date_2010_08_13_15_58_31/Data'
pathname2= base + 'aversive_date_2010_07_24_08_40_11/Data'

f = tables.openFile(filename)
data1 = persistence.load_object(f, pathname1)
data2 = persistence.load_object(f, pathname2)

from cns.experiment.data.aversive_data import AnalyzedAversiveData, \
        GrandAnalyzedAversiveData

analyzed = GrandAnalyzedAversiveData(data=[AnalyzedAversiveData(data=data1), 
                                           AnalyzedAversiveData(data=data2)])

print analyzed.remind_seq
print analyzed.par_fa_frac

from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView, TestView
#import numpy as np
#analyzed = AnalyzedAversiveData(data=data1)
view = AnalyzedAversiveDataView(analyzed=analyzed)
view.configure_traits()
#print len(analyzed.par_reaction_snippets)
#print np.array(analyzed.par_info)
#print np.array(analyzed.reaction_snippets).ravel()
#analyzed.configure_traits()

#from pylab import *
#for m, par in zip(analyzed.par_mean_warn_reaction_snippets, analyzed.pars):
#    plot(m, label=str(par))
#legend()
#show()
