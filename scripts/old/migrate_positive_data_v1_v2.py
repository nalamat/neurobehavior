import re
import tables
from cns.data.h5_utils import walk_nodes, extract_date_from_name, rgetattr
from cns.data.persistence import strftime
from cns.util.binary_funcs import ts, edge_rising
from datetime import timedelta

def migrate(file):
    f = tables.openFile(file, 'a')

    filter = {'_v_name': lambda name: name.startswith('appetitive_date')}
    for node in walk_nodes(f.root, filter=filter):
        newname = node._v_name.replace('appetitive_date',
                                       'PositiveDTExperiment')
        node._f_move(newname=newname)
        node.data._f_setAttr('klass', 'PositiveDTData')
        print 'Renamed node to %s' % node._v_name
        print 'Updated data class to %s' % node.data._v_attrs.klass

    # Correct the bad sampling frequency stored in PositiveData nodes
    #filter = {'_v_name': 'contact', '.OBJECT_VERSION': None }
    #for node in walk_nodes(f.root, filter=filter):
    #    if hasattr(node, 'spout_TTL'):
    #        fs = 195.3125
    #    elif hasattr('override_TTL'):
    #        fs = 976.5625
    #    for table in node._f_iterNodes():
    #        table._v_attrs.fs = fs
    #        print "Set node %s fs to %f" % (table._v_pathname, fs)

    ## Now that the bad sampling frequency has been corrected, fix the start, end
    ## and duration
    #filter = {'data._v_name': 'data', '.OBJECT_VERSION': None }
    #for node in walk_nodes(f.root, filter=filter):
    #    pre = node._v_name[:-19]
    #    start_time = extract_date_from_name(node, pre=pre)
    #    fs = node.data.contact.spout_TTL._v_attrs.fs
    #    total_samples = len(node.data.contact.spout_TTL)
    #    if fs == 0:
    #        print "ERROR", node._v_pathname
    #    else:
    #        duration = timedelta(seconds=total_samples/fs)
    #        stop_time = start_time + duration
    #        try:
    #            node._f_delAttr('start_time')
    #            node._f_delAttr('stop_time')
    #            node._f_delAttr('duration')
    #        except:
    #            pass
    #        node._f_setAttr('date', strftime(start_time.date()))
    #        node._f_setAttr('start_time', strftime(start_time))
    #        node._f_setAttr('stop_time', strftime(stop_time))
    #        node._f_setAttr('duration', duration)

    ## Correct the swapped hit_frac and fa_frac columns
    #filter = {'_v_name': 'par_info', '.OBJECT_VERSION': None }
    #for node in walk_nodes(f.root, filter=filter):
    #    t = node.read()
    #    if len(t) > 0:
    #        newdata = t['hit_frac'], t['fa_frac']
    #        colnames = 'fa_frac', 'hit_frac'
    #        node.modifyColumns(0, len(t), columns=newdata, names=colnames)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Migrate data to v2 format')
    parser.add_argument('file', type=str)
    args = parser.parse_args()
    migrate(args.file)
