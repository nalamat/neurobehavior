from cns.data import persistence
from cns.experiment.data.aversive_data import AnalyzedAversiveData
from numpy import array
from cns.util.math import d_prime
from cns.experiment.data import aversive_data, aversive_data_view
from cns.data import h5_utils
import tables
#node = f.getNode('/Cohort_0/animals/Animal_6/experiments/aversive_date_2010_08_17_17_06_16/')
#base = '/Cohort_0/animals/Animal_%d/'

import logging
logging.root.setLevel(logging.WARN)

def process_animal(node):
    #nodes = h5_utils.walk_nodes(node.experiments, klass='RawAversiveData*')
    with open('summary.txt', 'w') as fout:
        for subnode in node.experiments._f_listNodes():
            if 'aversive' in  subnode._v_name:
                print node._v_pathname
                data = persistence.load_object(node)
                analyzed = AnalyzedAversiveData(data=data)
                try:
                    fout.write('Experiment: ' + data.start_time.strftime('%x %X') + '\n')
                except AttributeError:
                    pass
                #fout.write(repr(analyzed.par_info))
                #print data.water_log[-1]
                #print analyzed.par_info

def process_node(node, summary):
    #par_info = node.Data.Analyzed.AnalyzedAversiveData_0.par_info[:]
    data = persistence.load_object(node.Data)
    analyzed = AnalyzedAversiveData(data=data)
    par_info = analyzed.par_info
    paradigm = persistence.load_object(node.Paradigm)
    if analyzed.data.total_trials < 20:
        return summary
    if paradigm.signal_warn.variable == 'ramp_duration':
        dB = 97-paradigm.signal_warn.attenuation
        for row in par_info:
            key = row[0], dB
            append = row[1:5]
            summary[key] = summary.get(key, array([0, 0, 0, 0])) + append
    elif paradigm.signal_warn.variable == 'attenuation':
         dur = paradigm.signal_warn.ramp_duration
         for row in par_info:
            key = dur, 97-row[0]
            append = row[1:5]
            summary[key] = summary.get(key, array([0, 0, 0, 0])) + append
    return summary

'''
data = {}
for group in f.walkGroups():
    animals = {}
    if 'klass' in group._v_attrs and group._v_attrs.klass == 'Animal':
        for node in group.experiments._v_children.values():
            if 'aversive' in node._v_name:
                try:
                    process_node(node, data)
                except persistence.PersistenceError:
                    pass
                except tables.FileModeError:
                    pass

keys = data.keys()
keys.sort()

grouped = {}
for k in keys:
    dur, dB = k
    value = data[k]
    grouped.setdefault(dur, []).append((dB, d_prime(*value))) 

from pylab import *
i = 1
for k, v in grouped.items():
    title('%f' % k)
    subplot(4, 4, i);
    v.sort()
    plot(*zip(*v))
    i += 1

show()
'''
if __name__ == '__main__':
    #filename = 'c:/users/brad/desktop/BNB_dt_group_5_control.cohort.hd5'
    filename = '/home/brad/projects/data/BNB_dt_group_5_control.cohort.hd5'
    f = tables.openFile(filename, 'r')
    process_animal(f.root.Cohort_0.animals.Animal_0)
