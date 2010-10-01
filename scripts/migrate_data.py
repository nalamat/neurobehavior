'''
- A new AversiveData structure was created that was not backwards-compatible
with the original AversiveData structure.  Consequently, we implemented a
versioning scheme (RawAversiveData_v0_1, RawAversiveData_v0_2, etc).
AversiveData was renamed to RawAversiveData_v0_1 during this process.  This
function scans the file for any references to the old classname and updates it
to the correct classname.

- Experiment start time was originally stored in the name of the node for the
experiment itself.  Newer versions of the program store it as an attribute in
the Data node (as well as stop_time).  This function scans the file for
experiment data missing the start_time and stop_time attributes.  If missing,
the start_time is derived from the name of the node, while stop_time is
estimated by checking the last timestamp recorded in that experiment.
'''

import tables
import logging
log = logging.getLogger(__name__)

def fix_node_class(node):
    '''
    Fix node class
    '''
    try:
        if node._v_attrs.klass == 'AversiveData':
            node._v_attrs.klass = 'RawAversiveData_v0_2'
            print 'corrected node ' + node._v_pathname
        if node._v_attrs.klass == 'RawAversiveData_v0_1':
            node._v_attrs.klass = 'RawAversiveData_v0_2'
            print 'corrected node ' + node._v_pathname
    except:
        pass

def fix_node_metadata(node):
    '''
    Fix missing start_time, stop_time and duration attribute
    '''
    from cns.data.h5_utils import extract_date_from_name
    from cns.data import persistence
    from datetime import timedelta

    name = node._v_name
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
                # in kall of the channel types
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

def fix_node_contact(node):
    '''
    Convert old 2D storage format for contact data to separate arrays for each
    "channel" of data.
    '''
    import numpy as np
    from cns.channel import FileChannel
    from cns.data.h5_utils import append_node

    if node._v_name == 'contact' and isinstance(node, tables.Array):
        print 'Updating contact data for node %s' % node._v_pathname
        parent = node._v_parent
        node._f_move(newname='temp_contact')
        fs = node._v_attrs.fs

        contact_node = append_node(parent, 'contact')

        channels = ((0, 'touch_digital', np.bool),
                    (1, 'touch_digital_mean', np.float32),
                    (2, 'touch_analog', np.float32),
                    (3, 'trial_running', np.bool),
                   )

        for i, name, dtype in channels:
            channel = FileChannel(node=contact_node, name=name, fs=fs,
                                  dtype=dtype)
            channel.write(node[:,i])

        node._f_remove()

def fix_node_names(node):
    '''
    Update old naming conventions to match new naming conventions.
    '''
    import re

    if re.match('^date(\d+)', node._v_name):
        print 'Renaming node %s' % node._v_pathname
        node._f_move(newname='aversive_date_' + node._v_name[4:],
                     newparent=node._v_parent.experiments)
        node.AversiveData._f_move(newname='Data')
        node.AversiveParadigm_0._f_move(newname='Paradigm')
        node.Data.AnalyzedAversiveData_0._f_move(newparent=node._v_pathname + \
                                                 '/Data/Analyzed',
                                                 createparents=True)

    try:
        if 'trial_data' in node._v_children:
            print 'Renaming trial_log and trial_data in node %s' % node._v_pathname
            if 'trial_log' in node._v_children:
                node.trial_log._f_move(newname='event_log')
            node.trial_data._f_move(newname='trial_log')
    except AttributeError:
        pass

def fix_legacy_data(file):
    f = tables.openFile(file, 'a')
    log.info('Updating node class metadata')
    for node in f.walkNodes():
        fix_node_class(node)
    log.info('Updating node names and paths')
    for node in f.walkNodes():
        fix_node_names(node)
    log.info('Updating node contact data')
    for node in f.walkNodes():
        fix_node_contact(node)
    log.info('Updating missing node metadata')
    for node in f.walkNodes():
        fix_node_metadata(node)

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2:
        fix_legacy_data(sys.argv[1])
