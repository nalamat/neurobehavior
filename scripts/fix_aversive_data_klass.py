'''
A new AversiveData structure was created that was not backwards-compatible with
the original AversiveData structure.  Consequently, we implemented a versioning
scheme (RawAversiveData_v0_1, RawAversiveData_v0_2, etc).  AversiveData was
renamed to RawAversiveData_v0_1 during this process.  This function scans the
file for any references to the old classname and updates it to the correct
classname.
'''
import tables
import sys
from cns.data.h5_utils import extract_date_from_name
from cns.data import persistence
from datetime import timedelta

def fix_legacy_data(file):
    f = tables.openFile(file, 'a')
    for node in f.walkNodes():
        # Fix class reference
        try:
            if node._v_attrs.klass == 'AversiveData':
                node._v_attrs.klass = 'RawAversiveData_v0_1'
                print 'corrected node ' + node._v_pathname
        except:
            pass
        
        # Fix missing start_time, stop_time and duration attribute
        name = node._v_name
        #if name.startswith('date') or name.startswith('aversive_date_'):
        if name.startswith('aversive_date_'):
            try: 
                node.Data._v_attrs.start_time
            except:
                if name.startswith('date'):
                    start_time = extract_date_from_name(node, pre='date')
                else:
                    start_time = extract_date_from_name(node, 
                                                        pre='aversive_date_')
                print node._v_pathname
                print start_time
                try:
                    fs = node.Data.contact._v_attrs.fs
                except:
                    # Trial running is the only array that is reliably present
                    # in all of the channel types
                    fs = node.Data.contact.trial_running._v_attrs.fs
                    
                try:
                    ts = node.Data.water_log[-1][0]
                except:
                    try:
                        ts = node.Data.trial_data[-1][0]
                    except:
                        print 'aborted experiment, setting ts to 0'
                        ts = 0
                
                try:
                    # Guess duration of experiment from last timestamp recorded
                    # in the water log and computing number of seconds based on
                    # sampling frequency.
                    duration = timedelta(seconds=ts/fs)
                    stop_time = start_time + duration
                    node.Data._v_attrs.start_time = persistence.strftime(start_time)
                    node.Data._v_attrs.stop_time = persistence.strftime(stop_time)
                    #node.Data._v_attrs.duration = duration
                    print 'Recovered duration for ', node._v_pathname
                except BaseException, e:
                    print 'Unable to recover duration for ', node._v_pathname
                    print e
                
#            if node._v_name.startswith('date') or node
#            if hasattr(node._v_attrs, 'klass'):
#                if 'RawAversiveData' in node._v_attrs.klass:
#                    node._v_attrs.start_time
#        except:
#            #print node._v_pathname
#            try:
#                print parse_date_node(node._v_parent, pre='aversive_date_')
#            except:
#                print parse_date_node(node._v_parent, pre='date')
#            print 'missing start time'

if __name__ == '__main__':
    if len(sys.argv) == 2:
        fix_legacy_data(sys.argv[1])
