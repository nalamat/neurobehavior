from __future__ import division

import tables
import sys
import pandas
import numpy as np

import h5

def update_progress(i, n, mesg, progress_character='.'):

    '''
    Progress bar for use with the command line
    '''
    max_chars = 40
    progress = i/n
    num_chars = int(progress*max_chars)
    num_left = max_chars-num_chars
    # The \r tells the cursor to return to the beginning of the line rather than
    # starting a new line.  This allows us to have a progressbar-style display
    # in the console window.
    template = '\r[{}{}] {:.0f}% {}   '
    sys.stdout.write(template.format(progress_character*num_chars, ' '*num_left,
                                     progress*100, mesg))

    # Force a flush because sometimes when using bash scripts and pipes, the
    # output is not printed until after the program exits.
    sys.stdout.flush()
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
        tl = pandas.DataFrame(base_node.trial_log[:])

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
        et = fh.root.event_data.timestamps[mask].astype('d')
        et.sort()
        return et

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

def create_extract_arguments_from_extracted(filename):

    with tables.openFile(filename, 'r') as fh:
        kwargs = {}
        processing = {}
        filter_node = fh.root.filter
        event_node = fh.root.event_data

        processing['bad_channels'] = list(filter_node.bad_channels[:]-1)
        processing['diff_mode'] = filter_node._v_attrs.diff_mode
        processing['filter_freq_lp'] = filter_node._v_attrs.fc_lowpass
        processing['filter_freq_hp'] = filter_node._v_attrs.fc_highpass
        processing['filter_btype'] = filter_node._v_attrs.filter_btype
        processing['filter_order'] = filter_node._v_attrs.filter_order

        kwargs['processing'] = processing
        kwargs['channels'] = event_node._v_attrs.extracted_channels-1
        kwargs['noise_std'] = event_node._v_attrs.noise_std
        kwargs['threshold_stds'] = event_node._v_attrs.threshold_std
        kwargs['rej_threshold_stds'] = event_node._v_attrs.reject_threshold_std
        kwargs['window_size'] = event_node._v_attrs.window_size
        kwargs['cross_time'] = event_node._v_attrs.cross_time

        return kwargs

def create_extract_arguments_from_raw(filename):

    with tables.openFile(filename, 'r') as fh:
        kwargs = {}
        md = h5.p_get_node(fh, '*/data/physiology/channel_metadata')

        processing = {}

        processing['diff_mode'] = md._v_attrs.diff_mode
        processing['filter_freq_lp'] = md._v_attrs.filter_freq_lp
        processing['filter_freq_hp'] = md._v_attrs.filter_freq_hp
        processing['filter_btype'] = md._v_attrs.filter_btype
        processing['filter_order'] = md._v_attrs.filter_order

        md = md.read()
        processing['bad_channels'] = [s['index'] for s in md if s['bad']]

        md = [s for s in md if s['extract']]

        # Gather the arguments required by the spike extraction routine
        kwargs['processing'] = processing
        kwargs['noise_std'] = [s['std'] for s in md]
        kwargs['channels'] = [s['index'] for s in md]
        kwargs['threshold_stds'] = [s['th_std'] for s in md]
        kwargs['rej_threshold_stds'] = [s['artifact_std'] for s in md]
        kwargs['window_size'] = 2.1
        kwargs['cross_time'] = 0.5  
        kwargs['cov_samples'] = 5e3 

        return kwargs

def create_extract_arguments(filename):
    if 'raw' in filename:
        return create_extract_arguments_from_raw(filename)
    elif 'extracted' in filename:
        return create_extract_arguments_from_extracted(filename)
    else:
        raise IOError, 'Unrecognized file type'

def load_curated_metadata(curated_file, single_unit=False):
    '''
    Load curated spike metadata from file generated by the nb_save_ums2000
    function

    Automatically discards garbage clusters.

    Parameters
    ----------
    curated_file : str
        file to load
    single_unit : bool
        Return only clusters that are identified as good single units

    Returns
    -------
    clusters : pandas.DataFrame
    '''

    # Hardcoded based on UMS2000 default settings
    cluster_type = pandas.Series({
        1:  'in process',
        2:  'good unit',
        3:  'multi-unit',
        4:  'garbage',
        5:  'needs outlier removal', })

    with tables.openFile(curated_file) as fh:
        c_id, c_type = fh.root.labels[:].astype('i')

        if 'cluster_stats' in fh.root:
            # See the documentation in matlab/nb_cluster_metrics.m for detail on
            # the information stored here.
            c_stats = fh.root.cluster_stats[:]

            # The probabilities are independent, so we can compute the overall false
            # positive and negative probabilities via the product.
            c_fp = 1-np.prod(1-fh.root.cluster_fp[:].T, axis=0)
            c_fn = 1-np.prod(1-fh.root.cluster_fn[:].T, axis=0)

            c_data = {
                'c_type':           map(cluster_type.get, c_type),
                'expected_rpv':     c_stats[2],
                'actual_rpv':       c_stats[5],
                'fraction_missing': c_stats[6],
                'isi_fraction':     c_stats[7],
                'false_positives':  c_fp,
                'false_negatives':  c_fn,
                'cluster':          c_id,
            }
        else:
            # No cluster statistics available.  Just return the basic
            # information.
            c_data = {
                'c_type':   map(cluster_type.get, c_type),
                'cluster':  c_id, }

        clusters = pandas.DataFrame(c_data).set_index('cluster')

        # Load the channels used to detect the spikes
        channels = fh.root.info.detect.detect_channels[:]
        channels = channels.ravel().astype('i').tolist()
        clusters['channels'] = [channels]*len(clusters)

    # Return only data with good single units (as defined by our criteria).
    # Eventually this should include the false positive and false negative
    # spike information.
    if single_unit:
        mask = (clusters.c_type == 'good unit') & \
               (clusters.fraction_missing <= 0.2) & \
               (clusters.isi_fraction < 0.5)
        clusters = clusters[mask]

    # Discarding the garbage must come at the end (since garbage data must
    # be included in the false positive and negative probabilities.
    clusters = clusters[clusters.c_type != 'garbage']

    return clusters

def load_curated(curated_file, single_unit=False):
    '''
    Load curated spike data generated by the nb_save_ums2000 function

    Automatically discards garbage clusters.

    Parameters
    ----------
    curated_file : str
        file to load
    single_unit : bool
        Return only clusters that are identified as good single units

    Returns
    -------
    TODO finish documenting
    spikes : pandas.DataFrame
    clusters : pandas.DataFrame
    channels : list
    '''
    clusters = load_curated_metadata(curated_file, single_unit)

    # Load the timestamps only if we have *good* data in the clusters (otherwise
    # we are wasting time reading in and discarding data).
    if len(clusters):
        with tables.openFile(curated_file) as fh:
            assigns = fh.root.assigns[:].ravel() # Cluster ID of each ts
            ts = fh.root.spiketimes[:].ravel()   # Time of each spike
            spikes = pandas.DataFrame({'cluster': assigns, 'ts': ts})

            # This discards bad data by discarding all data in spikes that do
            # not contain the corresponding cluster ID in clusters.
            spikes = spikes.join(clusters, on='cluster', how='right')
            spikes = spikes[['ts', 'cluster']]
    else:
        # Initialize an empty dataframe
        spikes = pandas.DataFrame({'cluster': [], 'ts': []})

    return spikes, clusters
def load_censored_epochs(ext_filename, channels=None):
    '''
    Given the extracted trial times file (containing the RMS noise floor data),
    return a list of the epochs indicating regions that need to be censored in
    the dataset.  You are still responsible for figuring out whether these
    regions impinge on the time windows you are analyzing (hint ... see
    `cns.util.binary_funcs.epochs_contain` for help)

    Channels are 0-based index
    '''

    with tables.openFile(ext_filename) as fh:
        ext_channels = fh.root.event_data._v_attrs.extracted_channels.tolist()
        if channels is None:
            channels = ext_channels
        elif not np.iterable(channels):
            channels = [channels]
        cepochs = []
        for channel in channels:
            i = ext_channels.index(channel)
            cnode = fh.root.censor._f_getChild('extracted_{}'.format(i))
            cepochs.extend(cnode.censored_epochs[:])
        return smooth_epochs(cepochs)

