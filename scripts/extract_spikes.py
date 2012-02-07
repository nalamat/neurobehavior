from __future__ import division

import cPickle as pickle
import tables
import numpy as np 
from scipy import signal

from cns.channel import ProcessedFileMultiChannel
from cns.arraytools import chunk_samples, chunk_iter

from cns import get_config
default_chunk_size = get_config('CHUNK_SIZE')

def median_std(x):
    '''
    Given a multichannel array, compute the standard deviation of the signal
    using the median algorithm described in Quiroga et al. (2004) and online
    (http://www.scholarpedia.org/article/Spike_sorting).

    # TODO: format this for latex
    \sigma_n = median {|x|/0.6745}
    '''
    return np.median(np.abs(x)/0.6745, axis=1)

def decimate_waveform(input_node, output_node, q, N=4, progress_callback=None,
                      chunk_size=default_chunk_size, include_ts_data=True):
    '''
    Decimates the waveform data to a lower sampling frequency using a lowpass
    filter cutoff.  Resulting decimation is saved under the physiology node as
    "raw_decimated_N" where N is the decimation factor.  If the data already
    exists from a prior run it will be overwritten.

    A 4th order lowpass butterworth filter is used in conjunction with filtfilt
    to apply a zero phase-delay to the waveform.

    This code is carefully designed to handle boundary issues when processing
    large datasets in chunks (e.g. stabilizing the edges of each chunk when
    filtering and extracting the correct samples from each chunk).

    Parameters
    ----------
    input_node : instance of tables.Group
        The PyTables group pointing to the root of the experiment node.  The
        physiology data will be found under input_node/physiology/raw.
    output_node : instance of tables.Group
        The target node to save the data to.  Note that this must be an instance
        of tables.Group since several arrays will be saved under the target
        node.
    output_node : instance of tables.Group
    q : int
        The downsampling (i.e. decimation) factor
    N : int
        The filter order to use
    progress_callback : callable
        Function to be notified each time a chunk is processed.  The function
        must take three arguments, (chunk number, total chunks, message).  As
        each chunk is processed, the function will be called with updates to the
        progress.  If the function returns a nonzero (True) value, the
        processing will terminate.
    chunk_size : float
        Maximum memory size (in bytes) each chunk should occupy
    include_ts_data : boolean
        Copy the trial log, timestamp and epoch data to the extracted times file
        as well.  This is useful for creating a smaller, more compact datafile
        that you can carry around with you rather than the raw multi-gigabyte
        physiology data.
    '''
    # Make a dummy progress callback if none is requested
    if progress_callback is None:
        progress_callback = lambda x, y, z: False

    # Load information about the data we are processing and compute the sampling
    # frequency for the decimated dataset
    raw = input_node.data.physiology.raw
    source_fs = raw._v_attrs['fs']
    target_fs = source_fs/q

    n_channels, n_samples = raw.shape
    n_dec_samples = np.floor(n_samples/q)

    fh_out = output_node._v_file
    filters = tables.Filters(complevel=1, complib='blosc', fletcher32=True)
    shape = (n_channels, n_dec_samples)
    lfp = fh_out.createCArray(output_node, 'lfp', raw.atom,
                              shape, "Lowpass filtered signal for LFP analysis",
                              filters=filters)

    # Critical frequency of the lowpass filter (ensure that the filter cutoff is
    # twice the target sampling frequency to avoid aliasing).
    Wn = target_fs*2/source_fs
    b, a = signal.iirfilter(N, Wn, btype='lowpass') # Defaults to butter
    
    # The number of samples in each chunk *must* be a multiple of the decimation
    # factor so that we can extract the *correct* samples from each chunk.
    c_samples = chunk_samples(raw, 10e6, q)
    dec_samples = int(c_samples/q)
    overlap = 3*len(b)
    iterable = chunk_iter(raw, c_samples, loverlap=overlap, roverlap=overlap)

    for i, chunk in enumerate(iterable):
        chunk = signal.filtfilt(b, a, chunk, padlen=0)

        # Now that we've filtered our chunk, we can discard the overlapping data
        # that was provided to help stabilize the edges of the filter while
        # decimating the remaining array.
        lb = i*dec_samples
        lfp[lb:lb+dec_samples] = chunk[overlap:-overlap:q]

        if progress_callback(i*c_samples, n_samples, ''):
            break

    # Save some data about how the lfp data was generated
    lfp._v_attrs['q'] = q
    lfp._v_attrs['fs'] = target_fs
    lfp._v_attrs['b'] = b
    lfp._v_attrs['a'] = a
    lfp._v_attrs['chunk_overlap'] = overlap
    lfp._v_attrs['ftype'] = 'butter'
    lfp._v_attrs['btype'] = 'lowpass'
    lfp._v_attrs['order'] = N
    lfp._v_attrs['freq_lowpass'] = target_fs*2

    if include_ts_data:
        copy_ts_data(input_node, output_node)

def copy_ts_data(input_node, output_node):
    '''
    Copy the behavior data (e.g. trial log, timestamps and epochs) over to the
    new node.
    '''
    to_copy = [('data/trial_log', 'trial_log'),
               ('data/physiology/epoch', 'physiology_epoch'),
               ('data/contact/trial_epoch', 'trial_epoch'),
               ('data/contact/poke_epoch', 'poke_epoch'),
               ('data/contact/signal_epoch', 'signal_epoch'),
               ('data/contact/all_poke_epoch', 'all_poke_epoch'),
               ('data/contact/response_ts', 'response_ts'),
              ]
    for (node_path, node_title) in to_copy:
        node = input_node._f_getChild(node_path)
        node._f_copy(output_node, newname=node_title)

def extract_spikes(input_node, output_node, channels, noise_std, threshold_stds,
                   rej_threshold_stds, processing, window_size=2.1,
                   cross_time=0.5, cov_samples=10000, progress_callback=None,
                   chunk_size=default_chunk_size, include_ts_data=True):
    '''
    Extracts spikes.  Lots of options.

    Parameters
    ----------
    input_node : instance of tables.Group
        The PyTables group pointing to the root of the experiment node.  The
        physiology data will be found under input_node/data/physiology/raw.
    output_node : instance of tables.Group
        The target node to save the data to.  Note that this must be an instance
        of tables.Group since several arrays will be saved under the target
        node.
    processing : dict
        Dictionary containing settings that will be passed along to
        ProcessedMultiChannel.  These serve as instructions for referencing and
        filtering of the data.  The dictionary must include the following
        elements:
            freq_lp : float (Hz)
                The lowpass frequency
            freq_hp : float (Hz)
                The highpass frequency
            filter_order : int
                The filter order
            bad_channels : array-like
                List of bad channels using 0-based indexing
            diff_mode : ['all_good']
                Type of referencing to use.  Currently only one mode
                (referencing against all the good channels) is supported.
    noise_std : array-like (float)
        Standard deviation of the noise (used for computing actual threshold and
        reject threshold)
    channels : array-like (int)
        Channel indices (zero-based) to extract
    threshold_stds : array-like (float)
        Thresholds to use for the extracted channels (in standard deviations
        from the noise floor)
    rej_threshold_stds : array-like (float)
        Reject thresholds (in standard deviations from the noise floor)
    window_size : float (msec)
        Window to extract.  Note that UMS2000 has a max_jitter option that will
        clip the waveform used for sorting by that amount (e.g. the final window
        size will be window_size-max_jitter).  Be sure to include a little extra
        data when pulling the data out to compensate.
    cross_time : float (msec)
        Alignment point for peak of waveform
    cov_samples : int
        Number of samples to collect for estimating the covariance matrix (used
        by UMS2000)
    progress_callback : callable
        Function to be notified each time a chunk is processed.  The function
        must take three arguments, (chunk number, total chunks, message).  As
        each chunk is processed, the function will be called with updates to the
        progress.  If the function returns a nonzero (True) value, the
        processing will terminate.
    chunk_size : float
        Maximum memory size (in bytes) each chunk should occupy
    include_ts_data : boolean
        Copy the trial log, timestamp and epoch data to the extracted times file
        as well.  This is useful for creating a smaller, more compact datafile
        that you can carry around with you rather than the raw multi-gigabyte
        physiology data.
    '''
    # Make sure data is in the format we want
    channels = np.asarray(channels)
    noise_std = np.asarray(noise_std)
    threshold_stds = np.asarray(threshold_stds)
    rej_threshold_stds = np.asarray(rej_threshold_stds)
    thresholds = noise_std * threshold_stds
    rej_thresholds = noise_std * rej_threshold_stds

    # Make a dummy progress callback if none is requested
    if progress_callback is None:
        progress_callback = lambda x, y, z: False

    # Load the physiology data and put a ProcessedMultiChannel wrapper around
    # it.  This wrapper will handle all the pertinent issues of referencing and
    # filtering (as well as chunking the data).
    node = ProcessedFileMultiChannel.from_node(input_node.data.physiology.raw,
                                               **processing)
    fs = node.fs

    n_channels = len(channels)
    total_samples = node.shape[-1]

    # Convert msec to number of samples
    window_samples = int(np.ceil(window_size*fs*1e-3))
    samples_before = int(np.ceil(cross_time*fs*1e-3))
    samples_after = window_samples-samples_before

    # Compute chunk settings
    loverlap = samples_before
    roverlap = samples_after
    c_samples = chunk_samples(node, chunk_size)

    # Now, create the nodes in the HDF5 file to store the data we extract.
    fh_out = output_node._v_file

    # Ensure that underlying datatype of HDF5 array containing waveforms is
    # identical to the datatype of the source waveform (e.g. 32-bit float).
    # EArrays are a special HDF5 array that can be extended dynamically on-disk
    # along a single dimension.
    size = (0, n_channels, window_samples)
    atom = tables.Atom.from_dtype(node.dtype)
    fh_waveforms = fh_out.createEArray(output_node, 'waveforms', atom, size)

    # If we have a sampling rate of 12.5 kHz, storing indices as a 32-bit
    # integer allows us to locate samples in a continuous waveform of up to 49.7
    # hours in duration.  This is more than sufficient for our purpose (we will
    # likely run into file size issues well before this point anyway).
    fh_indices = fh_out.createEArray(output_node, 'timestamps',
                                     tables.Int32Atom(), (0,))
    
    # The actual channel the event was detected on.  We can represent up
    # to 32,767 channels with a 16 bit integer.  This should be
    # sufficient for at least the next year.
    fh_channels = fh_out.createEArray(output_node, 'channels',
                                      tables.Int16Atom(), (0,))

    # This is another way of determining which channel the event was detected
    # on.  Specifically, if we are saving waveforms from channels 4, 5, 9, and
    # 15 to the HDF5 file, then events detected on channel 4 would be marked as
    # 4 in /channels and 0 in /channels index.  Likewise, events detected on
    # channel 9 would be marked as 3 in /channels_index.  This allows us to
    # "slice" the /waveforms array if needed to get the waveforms that triggered
    # the detection events.  
    #
    # >>> detected_waveforms = waveforms[:, channels_index, :] 
    #
    # This is also useful for UMS2000 becaues UMS2000 only sees the extracted
    # waveforms and assumes they are numbered consecutively starting at 1.  By
    # adding 1 to the values stored in this array, this can be used for the
    # event_channel data provided to UMS2000.
    fh_channel_indices = fh_out.createEArray(output_node, 'channel_indices',
                                             tables.Int16Atom(), (0,))

    # We can represent up to 256 values with an 8 bit integer.  That's overkill
    # for a boolean datatype; however Matlab doesn't support pure boolean
    # datatypes in a HDF5 file.  Lame.  Artifacts is a 2d array of [event,
    # channel] indicating, for each event, which channels exceeded the artifact
    # reject threshold.
    size = (0, n_channels)
    fh_artifacts = fh_out.createEArray(output_node, 'artifacts',
                                       tables.Int8Atom(), size)

    # Save some metadata regarding the preprocessing of the data (e.g.
    # referencing and filtering) and feature extraction parameters.
    fh_out.setNodeAttr(output_node, 'fs', node.fs)

    # This needs to be an EArray rather than an attribute or typical Array
    # because setNodeAttr() and createArray complain if you attempt to pass an
    # empty array to it (I think this is actually an implementation issue with
    # the underlying HDF5 library).  By doing this workaround, we can ensure
    # that empty arrays (i.e. no bad channels) can also be saved.
    fh_bad_channels = fh_out.createEArray(output_node, 'bad_channels',
                                          tables.Int8Atom(), (0,))
    fh_bad_channels.append(np.array(node.bad_channels)+1)

    filter_node = fh_out.createGroup(output_node, 'filter')

    # Currently we only support one referencing mode (i.e. reference against the
    # average of the good channels) so I've hardcoded this attribute for now.
    fh_out.setNodeAttr(filter_node, 'diff_mode', node.diff_mode)
    fh_out.createArray(filter_node, 'differential', node.diff_matrix)

    # Since we conventionally count channels from 1, convert our 0-based index
    # to a 1-based index.  It's OK to set these as node attributes becasue they
    # will never be empty arrays.  However, let's keep consistency and make
    # everything that's an array an array.
    fh_out.createArray(output_node, 'extracted_channels', channels+1)
    fh_out.createArray(output_node, 'noise_std', noise_std)

    # Be sure to save the filter coefficients used (not sure if this is
    # meaningful).  The ZPK may be more useful in general.  Unfortunately, HDF5
    # does not natively support complex numbers and I'm not inclined to deal
    # with the issue at present.
    fh_out.setNodeAttr(output_node, 'fc_lowpass', node.filter_freq_lp)
    fh_out.setNodeAttr(output_node, 'fc_highpass', node.filter_freq_hp)
    fh_out.setNodeAttr(output_node, 'filter_order', node.filter_order)
    fh_out.setNodeAttr(output_node, 'filter_btype', node.filter_btype)
    fh_out.setNodeAttr(output_node, 'filter_padding', node._padding)

    b, a = node.filter_coefficients
    fh_out.createArray(output_node, 'filter_b', b)
    fh_out.createArray(output_node, 'filter_a', a)

    # Chunk settings
    fh_out.setNodeAttr(output_node, 'chunk_samples', c_samples)
    fh_out.setNodeAttr(output_node, 'chunk_loverlap', loverlap)
    fh_out.setNodeAttr(output_node, 'chunk_roverlap', roverlap)

    # Feature extraction settings
    fh_out.setNodeAttr(output_node, 'window_size', window_size)
    fh_out.setNodeAttr(output_node, 'cross_time', cross_time)
    fh_out.setNodeAttr(output_node, 'samples_before', samples_before)
    fh_out.setNodeAttr(output_node, 'samples_after', samples_after)
    fh_out.setNodeAttr(output_node, 'window_samples', window_samples)
    fh_out.createArray(output_node, 'threshold', thresholds)
    fh_out.createArray(output_node, 'reject_threshold', rej_thresholds)
    fh_out.createArray(output_node, 'threshold_std', threshold_stds)
    fh_out.createArray(output_node, 'reject_threshold_std', rej_threshold_stds)

    # Allocate a temporary array, cov_waves, for storing the data used for
    # computing the covariance matrix required by UltraMegaSort2000.  Ensure
    # that the datatype matches the datatype of the source waveform.
    cov_waves = np.empty((cov_samples, n_channels, window_samples),
                         dtype=node.dtype)

    # Start indices of the random waveform segments to extract for the
    # covariance matrix.  Ensure that the randomly selected start indices are
    # always <= (total number of samples in each channel)-(size of snippet to
    # extract) so we don't attempt to pull out a snippet at the very end of the
    # session.
    cov_indices = np.random.randint(0, node.n_samples-window_samples,
                                    size=cov_samples)

    # Sort cov_indices for speeding up the search and extract process (each time
    # we load a new chunk, we'll walk through cov_indices starting at index
    # cov_i, pulling out the waveform, then incrementing cov_i by one until we
    # hit an index that is sitting inside the next chunk.
    cov_indices = np.sort(cov_indices)
    cov_i = 0

    thresholds = thresholds[:, np.newaxis]
    signs = np.ones(thresholds.shape)
    signs[thresholds < 0] = -1
    thresholds *= signs

    rej_thresholds = rej_thresholds[np.newaxis, :, np.newaxis]

    # Keep the user updated as to how many candidate spikes they're getting
    tot_features = 0

    iterable = chunk_iter(node, c_samples, loverlap, roverlap,
                          ndslice=np.s_[channels, :])

    for i_chunk, chunk in enumerate(iterable):
        # Truncate the chunk so we don't look for threshold crossings in the
        # portion of the chunk that overlaps with the following chunk.  This
        # prevents us from attempting to extract partial spikes.  Finally, flip
        # the waveforms on the pertinent channels (where we had a negative
        # threshold requested) so that we can perform the thresholding on all
        # channels at the same time using broadcasting.
        c = chunk[..., samples_before:-samples_after] * signs
        crossings = (c[..., :-1] <= thresholds) & (c[..., 1:] > thresholds)

        # Get the channel number and index for each crossing.
        channel_index, sample_index = np.where(crossings) 

        # Waveforms is likely to be reasonably large array, so preallocate for
        # speed.  It may actually be faster to just hand it directly to PyTables
        # for saving to the HDF5 file since PyTables handles caching of writes.
        n_features = len(sample_index)
        waveforms = np.empty((n_features, n_channels, window_samples),
                             dtype=node.dtype)

        # Loop through sample_index and pull out each waveform set.
        for w, s in zip(waveforms, sample_index):
            w[:] = chunk[..., s:s+window_samples]
        fh_waveforms.append(waveforms)

        # Find all the artifacts.  First, check the entire waveform array to see
        # if the signal exceeds the artifact threshold defined on any given
        # sample.  Note that the specified reject threshold for each channel
        # will be honored via broadcasting of the array.
        artifacts = (waveforms >= rej_thresholds) | \
                    (waveforms < -rej_thresholds)

        # Now, reduce the array so that we end up with a 2d array [event,
        # channel] indicating whether the waveform for any given event exceed
        # the reject threshold specified for that channel.
        artifacts = np.any(artifacts, axis=-1)
        fh_artifacts.append(artifacts)

        tot_features += len(waveforms)

        # The indices saved to the file must be referenced to t0.  Since we're
        # processing in chunks and the indices are referenced to the start of
        # the chunk, not the start of the experiment, we need to correct for
        # this.  The number of chunks processed is stored in i_chunk.
        fh_indices.append(sample_index+i_chunk*c_samples)

        # Channel on which the event was detected
        fh_channels.append(channels[channel_index]+1)
        fh_channel_indices.append(channel_index)

        # Check to see if any of the samples requested for the covariance matrix
        # lie in this chunk.  If so, pull them out.
        chunk_lb = i_chunk*c_samples
        chunk_ub = chunk_lb+c_samples
        while True:
            if cov_i == cov_samples:
                break
            index = cov_indices[cov_i]
            if index >= chunk_ub:
                break
            index = index-chunk_lb
            cov_waves[cov_i] = chunk[..., index:index+window_samples]
            cov_i += 1

        # Update the progress callback each time we finish processing a chunk.
        # If the progress callback returns True, end the processing immediately.
        mesg = 'Found {} features'.format(tot_features)
        if progress_callback(i_chunk*c_samples, total_samples, mesg):
            break

    # If the user explicitly requested a cancel, compute the covariance
    # matrix only on the samples we were able to draw from the data.
    cov_waves = cov_waves[:cov_i]

    # Compute the covariance matrix in the format required by
    # UltraMegaSort2000 (note by Brad -- I don't fully understand the
    # intuition here, but this should be the correct format required).
    cov_waves.shape = cov_i, -1
    cov_matrix = np.cov(cov_waves.T)
    fh_out.createArray(output_node, 'covariance_matrix', cov_matrix)
    fh_out.createArray(output_node, 'covariance_data', cov_waves)

    if include_ts_data:
        copy_ts_data(input_node, output_node)

def update_progress(i, n, mesg):
    '''
    Command-line progress bar.  Progress must be a fraction in the range [0, 1].
    '''
    import sys
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

if __name__ == '__main__':
    import sys
    process_batchfile(sys.argv[1])
