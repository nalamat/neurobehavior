from __future__ import division

import cPickle as pickle
import tables
import numpy as np 
import re
from os import path

from cns.channel import ProcessedFileMultiChannel

noise_std = lambda x: np.median(np.abs(x)/0.6745, axis=1)

def compute_noise_std(input_file, experiment_path, lb, ub):
    node = self.model.physiology_data
    channels = self.model.extract_channels
    chunk_samples = int(node.chunk_samples(CHUNK_SIZE)*0.1)
    chunk = node[:,chunk_samples:2*chunk_samples]
    stdevs = np.median(np.abs(chunk)/0.6745, axis=1)
    for std, setting in zip(stdevs, self.model.channel_settings):
        setting.std = std

def decimate_waveform(x, fs, q, differential=None, N=4):
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
    input_file : str
        File containing the experiment data
    experiment_path : str
        Path to location of experiment node in the HDF5 tree.  A HDF5 node can
        contain multiple experiments, so it's important to specify which
        experiment is being processed.
    q : int
        The downsampling (i.e. decimation) factor
    differential : 2D array
        The differential matrix containing the referencing configuration.  If
        None, the identity matrix will be used.
    N : int
        The filter order to use
    '''
    # Load information about the data we are processing and compute the sampling
    # frequency for the decimated dataset
    fh_in = tables.openFile(input_file, 'a', rootUEP=experiment_path)
    physiology = fh_in.root.data.physiology
    raw = physiology.raw
    source_fs = raw._v_attrs['fs']
    target_fs = source_fs/q

    n_channels, n_samples = raw.shape
    n_dec_samples = np.floor(n_samples/q)

    filters = tables.Filters(complevel=1, complib='blosc', fletcher32=True)
    shape = (n_channels, n_dec_samples)
    lfp = fh_in.createCArray(physiology, 'lfp_{}'.format(q), raw.atom, shape,
                             "Lowpass filtered signal for LFP analysis",
                             filters=filters)

    # Critical frequency of the lowpass filter (ensure that the filter cutoff is
    # twice the target sampling frequency to avoid aliasing).
    Wn = target_fs*2/source_fs
    b, a = signal.iirdesign(N, Wn, btype='lowpass') # Defaults to butter
    
    # The number of samples in each chunk *must* be a multiple of the decimation
    # factor so that we can extract the *correct* samples from each chunk.
    samples = chunk_samples(raw, 10e6, q)
    dec_samples = samples/q
    overlap = 2*len(b)
    iterable = chunk_iter(raw, samples, loverlap=overlap, roverlap=overlap,
                          pad_value=0)
    for i, chunk in enumerate(iterable):
        # Technically the documentation says the identity matrix will be used,
        # but we might as well skip that step (and the computational power)
        # because the result will be the same.
        if differential is not None:
            chunk = differential.dot(chunk)
        chunk = signal.filtfilt(chunk, b, a)

        # Now that we've filtered our chunk, we can discard the overlapping data
        # that was provided to help stabilize the edges of the filter while
        # decimating the remaining array.
        lb = i*dec_samples
        lfp[lb:lb+dec_samples] = chunk[overlap:-overlap:q]

    # Save some data about how the lfp data was generated
    lfp._v_attrs['q'] = q
    lfp._v_attrs['fs'] = target_fs
    lfp._v_attrs['b'] = b
    lfp._v_attrs['a'] = a
    lfp._v_attrs['differential'] = differential
    lfp._v_attrs['chunk_overlap'] = overlap
    lfp._v_attrs['ftype'] = 'butter'
    lfp._v_attrs['btype'] = 'lowpass'
    lfp._v_attrs['order'] = N
    lfp._v_attrs['freq_lowpass'] = target_fs*2

    fh_in.close()

def chunk_samples(x, max_bytes=10e6, block_size=None, axis=-1):
    '''
    Compute number of samples per channel to load based on the preferred memory
    size of the chunk (as indicated by max_bytes) and the underlying datatype.

    This code is carefully designed to handle boundary issues when processing
    large datasets in chunks (e.g. stabilizing the edges of each chunk when
    filtering and extracting the correct samples from each chunk).

    Parameters
    ----------
    x : ndarray
        The array that will be chunked
    max_bytes : int
        Maximum chunk size in number of bytes.  A good default is 10 MB (i.e.
        10e6 bytes).  The actual chunk size may be smaller than requested.
    axis : int
        Axis over which the data is chunked.
    block_size : None
        Ensure that the number of samples is a multiple of block_size. 

    Examples
    --------
    >>> x = np.arange(10e3, dtype=np.float64)   # 8 bytes per sample
    >>> chunk_samples(x, 800)
    100
    >>> chunk_samples(x, 10e3)                  # 10 kilobyte chunks
    1250
    >>> chunk_samples(x, 10e3, block_size=500)
    1000
    >>> chunk_samples(x, 10e3, block_size=300)
    1200
    >>> x.shape = 5, 2e3
    >>> chunk_samples(x, 800)
    20
    >>> chunk_samples(x, 10e3)
    250

    If the array cannot be broken up into chunks that are no greater than the
    maximum number of bytes specified, an error is raised:

    >>> x = np.ones((10e3, 100), dtype=np.float64)
    >>> chunk_samples(x, 1600)
    Traceback (most recent call last):
        ...
    ValueError: cannot achieve requested chunk size

    This is OK, however, because we are chunking along the first axis:

    >>> chunk_samples(x, 1600, axis=0)
    2
    '''
    bytes = np.nbytes[x.dtype]

    # Compute the number of elements in the remaining dimensions.  E.g. if we
    # have a 3D array of shape (2, 16, 1000) and wish to chunk along the last
    # axis, then the number of elements in the remaining dimensions is 2x16).
    shape = list(x.shape)
    shape.pop(axis)
    elements = np.prod(shape)
    samples = np.floor(max_bytes/elements/bytes)
    if block_size is not None:
        samples = np.floor(samples/block_size)*block_size
    if not samples:
        raise ValueError, "cannot achieve requested chunk size"
    return int(samples)
    
def chunk_iter_2D(x, chunk_samples, loverlap=0, roverlap=0, pad_value=np.nan):
    '''
    Return an iterable that yields the data in chunks.  Only supports chunking
    along the last axis at the moment.

    x : ndarray
        The array that will be chunked
    chunk_samples : int
        Number of samples per chunk along the specified axis
    loverlap : int
        Number of samples on the left to overlap with prior chunk (used to
        handle extraction of features that cross chunk boundaries)
    roverlap : int
        Number of samples on the right to overlap with the next chunk (used
        to handle extraction of features that cross chunk boundaries)
    pad_value : numeric
        Value to pad first chunk with if loverlap is > 0 and last chunk if
        roverlap is > 0
    '''
    channels, samples = x.shape

    i = 0
    while i < samples:
        lb = i-loverlap
        ub = i+n_samples+roverlap

        # If we are on the first chunk or last chunk, we have some special-case
        # handling to take care of.
        lpadding, rpadding = 0, 0
        if lb < 0:
            lpadding = np.abs(lb)
            lb = 0
        if ub > self.n_samples:
            rpadding = ub-self.n_samples
            ub = self.n_samples

        # Pull out the chunk and pad if needed
        chunk = self[..., lb:ub]
        if lpadding or rpadding:
            lchunk = np.ones((channels, lpadding))
            rchunk = np.ones((channels, rpadding))
            chunk = np.c_[lchunk, chunk, rchunk]

        yield chunk

def extract_spikes(input_node, output_node, channels, noise_std, threshold_stds,
                   rej_threshold_stds, processing, window_size=2.1,
                   cross_time=0.5, cov_samples=10000, progress_callback=None,
                   chunk_size=5e6):
    '''
    Extracts spikes

    Parameters
    ----------
    input_node : instance of tables.Array
        The PyTables Array containing the data to be processed (i.e. the "raw"
        array)
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
    node = ProcessedFileMultiChannel.from_node(input_node.physiology.raw,
                                               filter_mode='filtfilt',
                                               **processing)
    fs = node.fs

    ts_start = input_node.trial_log[0]['ts_start']
    ts_end   = input_node.trial_log[-1]['ts_end']

    n_channels = len(channels)
    chunk_samples = node.chunk_samples(chunk_size)

    # Convert msec to number of samples
    window_samples = int(np.ceil(window_size*fs*1e-3))
    samples_before = int(np.ceil(cross_time*fs*1e-3))
    samples_after = window_samples-samples_before

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

    # Currently we only support one referencing mode (i.e. reference against the
    # average of the good channels) so I've hardcoded this attribute for now.
    fh_out.setNodeAttr(output_node, 'diff_mode', node.diff_mode)
    fh_out.createArray(output_node, 'differential', node.diff_matrix)

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
    fh_out.setNodeAttr(output_node, 'fc_lowpass', node.freq_lp)
    fh_out.setNodeAttr(output_node, 'fc_highpass', node.freq_hp)
    fh_out.setNodeAttr(output_node, 'filter_order', node.filter_order)

    b, a = node.filter_coefficients
    fh_out.createArray(output_node, 'filter_b', b)
    fh_out.createArray(output_node, 'filter_a', a)

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

    # This is bullshit.  We need to do better.
    fh_out.createArray(output_node, 'experiment_range_ts', 
                       np.array([ts_start, ts_end]))

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

    # Keep the user updated as to how many candidate spikes they're
    # getting
    tot_features = 0

    # Now, loop through the data in chunks, identifying the spikes in each chunk
    # and loading them into the event times file.  The current chunk number is
    # tracked as i_chunk
    n_chunks = node.n_chunks(chunk_size)
    iterable = node.chunk_iter(chunk_size, channels, samples_before,
                               samples_after)

    for i_chunk, chunk in enumerate(iterable):

        print 'processing', i_chunk, n_chunks

        # Update the progress callback each time we finish processing a chunk.
        # If the progress callback returns True, end the processing immediately.

        mesg = 'Found {} features'.format(tot_features)
        if progress_callback(i_chunk/n_chunks, mesg):
            break

        # Truncate the chunk so we don't look for threshold crossings in the
        # portion of the chunk that overlaps with the following chunk.  This
        # prevents us from attempting to extract partials spikes.  Finally, flip
        # the waveforms on the pertinent channels (where we had a negative
        # threshold requested) so that we can perform the thresholding on all
        # channels at the same time using broadcasting.
        c = chunk[..., samples_before:-samples_after] * signs
        crossings = (c[..., :-1] <= thresholds) & (c[..., 1:] > thresholds)

        # Get the channel number and index for each crossing.  Be sure to let
        # the user know what's going on.
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

        # Find all the artifacts and discard them.  First, check the entire
        # waveform array to see if the signal exceeds the artifact threshold
        # defined on any given sample.  Note that the specified reject threshold
        # for each channel will be honored via broadcasting of the array.
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
        fh_indices.append(sample_index+i_chunk*chunk_samples)

        # Channel on which the event was detected
        fh_channels.append(channels[channel_index]+1)
        fh_channel_indices.append(channel_index)

        # Check to see if any of the samples requested for the covariance matrix
        # lie in this chunk.  If so, pull them out.
        chunk_lb = i_chunk*chunk_samples
        chunk_ub = chunk_lb+chunk_samples
        while True:
            if cov_i == cov_samples:
                break
            index = cov_indices[cov_i]
            if index >= chunk_ub:
                break
            index = index-chunk_lb
            cov_waves[cov_i] = chunk[..., index:index+window_samples]
            cov_i += 1

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

def update_progress(progress, mesg):
    '''
    Command-line progress bar.  Progress must be a fraction.
    '''
    import sys
    # The \r tells it to return to the beginning of the line rather than
    # starting a new line.
    max_chars = 60
    num_chars = int(progress*max_chars)
    num_left = max_chars-num_chars
    sys.stdout.write('\r[{}{}] {:.2f}%'.format('#'*num_chars, 
                                               ' '*num_left,
                                               progress))

def process_batchfile(batchfile):
    fh = open(batchfile, 'r')
    failed_jobs = []
    print 'Processing jobs in', batchfile
    with open(batchfile, 'rb') as fh:
        while True:
            try:
                job = pickle.load(fh)
                job['progress_callback'] = update_progress
                print 'Processing', job['input_file']
                #extract_spikes(**job)
            except EOFError:
                break

    with open('failed_jobs.dat', 'wb') as fh:
        pickle.dump(failed_jobs, fh)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    #import sys
    #process_batchfile(sys.argv[1])
