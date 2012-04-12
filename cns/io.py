from __future__ import division

import tables
import sys
from pandas import DataFrame

import h5

def update_progress(i, n, mesg):
    '''
    Progress bar for use with the command line
    '''
    max_chars = 60
    progress = i/n
    num_chars = int(progress*max_chars)
    num_left = max_chars-num_chars
    # The \r tells the cursor to return to the beginning of the line rather than
    # starting a new line.  This allows us to have a progressbar-style display
    # in the console window.
    sys.stdout.write('\r[{}{}] {:.2f}%'.format('#'*num_chars, 
                                               ' '*num_left,
                                               progress*100))
    return False

def get_experiment_node(filename=None):
    '''
    Given a physiology experiment file containing multiple experiments, prompt
    the user for the experiment they'd like to analyze.  If only one experiment
    is present, no prompt will be generated.

    filename : str or None
        File to obtain experiment from.  If None, extract the argument from
        sys.argv[1]

    returns : (filename, node path)
    '''
    if filename is None:
        filename = sys.argv[1]

    with tables.openFile(filename, 'r') as fh:
        nodes = fh.root._f_listNodes()
        if len(nodes) == 1:
            return filename, nodes[0]._v_pathname
        elif len(nodes) == 0:
            return ''

        while True:
            print 'Available experiments to analyze'
            for i, node in enumerate(nodes):
                try:
                    trials = len(node.data.trial_log)
                except:
                    trials = 0
                print '{}. {} trials: {}'.format(i, trials, node._v_name)

            ans = raw_input('Which experiment would you like to analyze? ')
            try:
                ans = int(ans)
                if 0 <= ans < len(nodes):
                    break
                else:
                    print 'Invalid option'
            except ValueError:
                print 'Please enter the number of the experiment'
        return filename, nodes[ans]._v_pathname

def load_trial_log(filename, path='*/data'):
    '''
    Load the trial log from the experiment and populate it with epoch data
    collected during the experiment.

    Path can have wildcards in it, but must point to the data node (not the
    trial_log node).
    '''
    epochs = (
        'trial_epoch',
        'physiology_epoch',
        'poke_epoch',
        'signal_epoch',
        )

    with tables.openFile(filename) as fh:
        base_node = h5.p_get_node(fh.root, path)
        tl = DataFrame(base_node.trial_log[:])

        for epoch in epochs:
            basename = epoch.split('_')[0]
            node = base_node._f_getChild(epoch)
            data = node[:]

            # Save as a timestamp (i.e. the raw integer value)
            tl[basename + '_ts/']  = data[:,0]
            tl[basename + '_ts\\']  = data[:,1]

            # Save as seconds
            data = data.astype('f')/node._v_attrs['fs']
            tl[basename + '/']  = data[:,0]
            tl[basename + '\\']  = data[:,1]

        # Pull in response timestamps as well
        node = base_node._f_getChild('response_ts')
        tl['response_ts|'] = node[:]
        tl['response|'] =  node[:]/node._v_attrs['fs']

        return tl

def import_spikes(filename, channel, cluster_id=None):
    '''
    Load spiketimes from an *_extracted.hd5 file

    Parameters
    ----------
    filename : str
        HDF5 file containing the spiketimes
    channel : int
        Channel number (1-based) to load
    cluster_id : int or None
        ID of cluster to load.  If None, all clusters are returned.
    '''
    with tables.openFile(filename, 'r') as fh:
        mask = fh.root.event_data.channels[:] == channel
        if cluster_id is not None:
            mask = mask & (fh.root.event_data.assigns[:].ravel() == cluster_id)
        return fh.root.event_data.timestamps[mask].astype('d')

def copy_block_data(input_node, output_node):
    '''
    Copy the behavior data (e.g. trial log, timestamps and epochs) over to the
    new node.

    input_node : instance of tables.Group
        The PyTables group pointing to the root of the experiment node.  The
        block data will be found under input_node/data/contact/* and
        input_node/data/physiology/*.
    output_node : instance of tables.Group
        The pytables group to where the block data will be copied to.
    '''
    # Will need to update the to_copy list with nodes that can be found for the
    # aversive data structure as well.  It's OK if the node isn't present, it'll
    # just be skipped.
    to_copy = [('data/trial_log', 'trial_log'),
               ('data/physiology/epoch', 'physiology_epoch'),
               ('data/physiology/ts', 'physiology_ts'),
               ('data/contact/trial_epoch', 'trial_epoch'),
               ('data/contact/poke_epoch', 'poke_epoch'),
               ('data/contact/signal_epoch', 'signal_epoch'),
               ('data/contact/all_poke_epoch', 'all_poke_epoch'),
               ('data/contact/response_ts', 'response_ts'),
              ]
    for (node_path, node_title) in to_copy:
        try:
            # Remove the node if it already exists in the destination node
            if node_title in output_node:
                output_node._f_getChild(node_title)._f_remove()

            # Now, copy the node data
            node = input_node._f_getChild(node_path)
            node._f_copy(output_node, newname=node_title)
        except AttributeError:
            print 'Unable to find {}'.format(node_path)
