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

Repair functions must be run in a very specific order that's listed in the tuple
below.
'''

import tables
import logging
log = logging.getLogger(__name__)

def fix_node_class(node):
    '''
    Updates node class to RawAversiveData_v0_2.  Assumes that all "cleanup"
    functions have successfully been completed and the node, indeed, reflects
    v0_2 structure.
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

def fix_node_time(node):
    '''
    Fix missing start_time, stop_time and duration attribute.  Depends on
    new-style contact data.
    '''
    from cns.data.h5_utils import extract_date_from_name
    from cns.data import persistence
    from datetime import timedelta

    if node._v_name.startswith('aversive_date_'):
        try: 
            node.Data._v_attrs.start_time
        except:
            start_time = extract_date_from_name(node, pre='aversive_date_')
            try:
                fs = node.Data.contact.trial_running._v_attrs.fs
                ts = node.Data.trial_log[-1][0]
            except:
                print 'aborted experiment, setting ts to 0'
                ts = 0
            
            duration = timedelta(seconds=ts/fs)
            stop_time = start_time + duration
            node.Data._v_attrs.start_time = persistence.strftime(start_time)
            node.Data._v_attrs.stop_time = persistence.strftime(stop_time)
            print 'Recovered duration for ', node._v_pathname

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

def move_experiment_nodes(node):
    '''
    Some nodes were originally stored directly under the animal node or in a
    subgroup called behavior_experiments.  These nodes are moved to the
    experiments folder and the behavior_experiments subgroup is deleted.
    '''
    from cns.data.h5_utils import get_or_append_node

    if node._v_name == 'behavior_experiments':
        newparent = get_or_append_node(node._v_parent, 'experiments')
        for child in node:
            child._f_move(newparent=newparent)
            print 'Moved to experiments: ' + child._v_name
        node._f_remove()

    elif node._v_name.startswith('Animal'):
        newparent = get_or_append_node(node, 'experiments')
        for child in node:
            if 'date' in child._v_name:
                print 'Moved to experiments: ' + child._v_name
                child._f_move(newparent=newparent)

def fix_node_names(node):
    import re 

    if re.match('^date(\d+)', node._v_name):
        print 'Renaming node: ' + node._v_pathname
        node._f_move(newname='aversive_date_' + node._v_name[4:])

    if node._v_name == 'AversiveData':
        print 'Renaming node: ' + node._v_pathname
        node._f_move(newname='Data')

    if node._v_name == 'AversiveParadigm_0':
        print 'Renaming node: ' + node._v_pathname
        node._f_move(newname='Paradigm')

def move_analyzed_nodes(node):

    if node._v_pathname.endswith('Data/AnalyzedAversiveData_0'):
        newparent = node._v_parent._v_pathname + '/Analyzed'
        node._f_move(newparent=newparent, createparents=True)

def fix_node_attr_names(node):

    if hasattr(node, '_v_children'):
        if 'trial_data' in node._v_children:
            print 'Renaming trial_data: ' + node._v_name
            if 'trial_log' in node._v_children:
                print 'Renaming trial_log: ' + node._v_name
                node.trial_log._f_move(newname='event_log')
            node.trial_data._f_move(newname='trial_log')

cleanup = (move_experiment_nodes,
           move_analyzed_nodes,
           fix_node_attr_names,
           fix_node_names,
           fix_node_contact,
           fix_node_time,
           fix_node_class,
          )

def fix_legacy_data(file):
    d = tables.openFile(file, 'a')
    for f in cleanup:
        print 'Running function ' + f.__name__
        for node in d.walkNodes():
            f(node)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Migrate data to v2 format')
    parser.add_argument('file', type=str, nargs=1)
    op = parser.parse_args()
    fix_legacy_data(op.file[0])
