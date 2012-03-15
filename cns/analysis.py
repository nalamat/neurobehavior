from __future__ import division

import time
import tables
import numpy as np 
from numpy.lib.stride_tricks import as_strided
from scipy import signal
from os import path

from .channel import ProcessedFileMultiChannel
from .arraytools import chunk_samples, chunk_iter
from . import get_config
from .io import copy_block_data

default_chunk_size = get_config('CHUNK_SIZE')

import logging
log = logging.getLogger(__name__)

def rates(et, tt, bins):
    n_tt = len(tt)
    pst = (et-tt[np.newaxis].T).ravel()
    rates = []
    for lb, ub in bins:
        m = (pst >= lb) & (pst < ub)
        n_et = len(pst[m])
        rates.append(n_et/n_tt/(ub-lb))
    return np.array(rates)

def histogram(et, tt, width, lb, ub):
    '''
    Generate a histogram.  Units of each parameter can be in seconds, cycles,
    milliseconds, etc; however, they must be identical.

    Parameters
    ----------
    et : array-like
        Event times (i.e. spike times)
    tt : array-like
        Trigger times to reference event times to
    lb : float
        Lower bound of the bin range
    ub : float
        Upper bound of the bin range
    width : float
        Bin width

    Returns
    -------
    bins : array
        Lower edge of histogram bins
    rate : array of dtype float
        Spike rate in each bin
    '''
    bins = histogram_bins(width, lb, ub)
    pst = et-tt[np.newaxis].T
    n = np.histogram(pst, bins=bins)[0].astype('f')
    n = n/width/len(tt)
    return bins[:-1], n

def histogram_bins(bin_width, lb, ub):
    '''
    Compute the bins.  
    
    Numpy, Scipy and Matplotlib (Pylab) all come with histogram functions, but
    the autogeneration of the bins rarely are what we want them to be.  This
    makes sure that we get the bins we want.
    '''
    bins =  np.arange(lb, ub, bin_width)
    bins -= bins[np.argmin(np.abs(bins))]
    return bins

def zero_waveform(input_node, duration):
    '''
    Given the experiment data, zeros out both the raw physiology and TTL
    waveforms up to the specified duration.   Useful for eliminating transients
    in the physiology signal that occur just before the animal enters the cage.

    This is a destructive operation that manipulates the raw data and cannot be
    undone.  Be sure to backup your data.

    Parameters
    ----------
    input_node : instance of tables.Group
        The PyTables group pointing to the root of the experiment node.  The
        physiology data will be found under input_node/data/physiology/raw.
    duration : float (sec)
        Duration (in seconds) to zero out from the beginning of data
        acquisition.

    The value (in samples) that was zeroed out for each waveform will be stored
    as an attribute in the node for each waveform.
    '''

    nodes = (('physiology', 'raw'),
             ('contact', 'TO_TTL'),
             ('contact', 'poke_TTL'),
             ('contact', 'reaction_TTL'),
             ('contact', 'response_TTL'),
             ('contact', 'reward_TTL'),
             ('contact', 'signal_TTL'),
             ('contact', 'spout_TTL'),
            )

    for group_name, node_name in nodes:
        group = input_node.data._f_getChild(group_name)
        node = group._f_getChild(node_name)
        node_fs = node._v_attrs['fs']
        samples = int(duration*node_fs)

        # Logically NaN would be a reasonable value to use, but this
        # significantly slows down the online plotting of the data so let's just
        # use 0.
        node[..., :samples] = 0
        node._v_attrs['zero:samples'] = samples

def truncate_waveform(input_node, duration):
    '''
    Given the experiment data, truncates both the raw physiology and TTL
    waveforms after the specified duration.  Useful for eliminating transients
    in the physiology signal that occur when the headstage falls off or after
    the animal is removed from the cage.

    This is a destructive operation that manipulates the raw data and cannot be
    undone.  Be sure to backup your data.

    Parameters
    ----------
    input_node : instance of tables.Group
        The PyTables group pointing to the root of the experiment node.  The
        physiology data will be found under input_node/data/physiology/raw.
    duration : float (sec)
        Duration (in seconds) to zero out from the beginning of data
        acquisition.

    The value (in samples) that was zeroed out for each waveform will be stored
    as an attribute in the node for each waveform.
    '''
    nodes = (('physiology', 'raw'),
             ('contact', 'TO_TTL'),
             ('contact', 'poke_TTL'),
             ('contact', 'reaction_TTL'),
             ('contact', 'response_TTL'),
             ('contact', 'reward_TTL'),
             ('contact', 'signal_TTL'),
             ('contact', 'spout_TTL'),
            )

    for group_name, node_name in nodes:
        group = input_node.data._f_getChild(group_name)
        node = group._f_getChild(node_name)
        node_fs = node._v_attrs['fs']
        new_size = int(duration*node_fs)
        old_size = len(node)
        node.truncate(new_size)

        # If this is the first time we've truncated the waveform, add a note to
        # the node metadata so that we know we've manipulated it.
        if 'truncate:original_size' not in node._v_attrs:
            node._v_attrs['truncate:original_size'] = old_size

def median_std(x, axis=-1):
    '''
    Given a multichannel array, compute the standard deviation of the signal
    using the median algorithm described in Quiroga et al. (2004) and online
    (http://www.scholarpedia.org/article/Spike_sorting).

    # TODO: format this for latex
    \sigma_n = median {|x|/0.6745}
    '''
    return np.median(np.abs(x)/0.6745, axis=axis)

def running_rms(input_node, output_node, duration, step, processing,
                algorithm='mean', progress_callback=None,
                chunk_size=default_chunk_size):
    '''
    Compute the running RMS value of the noise floor using a sliding window

    Parameters
    ----------
    input_node : instance of tables.Group
        The PyTables group pointing to the root of the experiment node.  The
        physiology data will be found under input_node/data/physiology/raw.
    output_node : instance of tables.Group
        The target node to save the data to.  Note that this must be an instance
        of tables.Group since several arrays will be saved under the target
        node.
    duration : float (seconds)
        Duration of the window
    step : float (seconds)
        Step size to slide the window along the array
    processing : dict
        Dictionary containing settings that will be passed along to
        ProcessedMultiChannel.  These serve as instructions for referencing and
        filtering of the data.  The dictionary must include the following
        elements:
            freq_lp : float (Hz)
                The lowpass frequency
            freq_hp : float (Hz)
                The highpass frequency
            filter_btype : {'bandpass', 'lowpass', 'highpass'}
                Band type.  If lowpass or highpass, the appropriate cutoff
                frequency will be ignored.
            filter_order : int
                The filter order
            bad_channels : array-like
                List of bad channels using 0-based indexing
            diff_mode : ['all good']
                Type of referencing to use.  Currently only one mode
                (referencing against all the good channels) is supported.
    algorithm : {'median', 'mean'}
        Algorithm for computing the 'M' in RMS.  Using the median rather than
        the mean has been recommended by some scientists (e.g. Quiroga et al.,
        2004).
    progress_callback : callable
        Function to be notified each time a chunk is processed.  The function
        must take three arguments, (chunk number, total chunks, message).  As
        each chunk is processed, the function will be called with updates to the
        progress.  If the function returns a nonzero (True) value, the
        processing will terminate.
    '''
    # Make a dummy progress callback if none is requested
    if progress_callback is None:
        progress_callback = lambda x, y, z: False

    raw_node = input_node.data.physiology.raw
    channel = ProcessedFileMultiChannel.from_node(raw_node, **processing)
    channels, total_samples = raw_node.shape

    # Number of samples to use in estimating RMS in the sliding window
    window_samples = int(duration*channel.fs)

    # Step size of the sliding window
    window_step = int(step*channel.fs)

    # Number of samples in the chunk that the window will be slid across.  The
    # chunk sample must be a multiple of the window step size such that we can
    # segment the chunk into evenly-spaced, evenly-sized windows such that the
    # end of the last window falls precisely at the end of the chunk.  To do
    # this, we get a preliminary estimate of the number of samples that will be
    # in the chunk based on our requested memory size (i.e. chunk bytes).  We
    # then compute how many full windows are going to be present in this chunk.
    # We then need to take number of windows x window step and add the remaining
    # samples required by the last window to get our final chunk size!
    #
    #  <--------------->     This length is defined by the number of windows x
    #                        the window step
    #                   <>   This length is window_samples-window_step
    # [...................]
    # [1..   4..   7..    ]  <- Windows are 3 samples long and slide in 2 sample
    # [  2..   5..   8..  ]     increments along the chunk
    # [    3..   6..   9..]
    #                    ?.. <- Next chunk needs to overlap on the left edge
    #                           with this chunk to process this window.  The
    #                           degree of overlap is defined by
    #                           window_samples-window_step
    #
    # The above diagram illustrates a schematic of how the sliding window will
    # work.  The first row is our data chunk.  The rows below indicate the
    # windows (the number indicates the order the windows are pulled out).
    c_samples = chunk_samples(raw_node, chunk_size)
    window_n = np.floor((c_samples-window_samples)/window_step) + 1
    c_samples = window_n*window_step + (window_samples-window_step)
    c_samples = int(c_samples)
    c_loverlap = window_samples-window_step
    c_loverlap = int(c_loverlap)

    # Compute the argument values to pass to the as_strided function.  This
    # essentially reshapes a 2D array (channel, samples) into a 3D array of
    # overlapping windows (channel, window, samples).  To understand how this
    # code works, you need to understand how n-dimensional arrays are
    # represented in computer memory and indexed.  This is an in-depth
    # explanation that is outside the scope of this comment.
    new_shape = channels, window_n, window_samples

    # Create the output data node
    fh_out = output_node._v_file
    filters = tables.Filters(complevel=1, complib='zlib', fletcher32=True)
    rms = fh_out.createEArray(output_node, 'rms', raw_node.atom,
                              (channels, 0), filters=filters,
                              title='Running RMS of signal')

    # Save some data about how the RMS was computed

    rms._v_attrs['window_duration'] = duration
    rms._v_attrs['window_duration_samples'] = window_samples
    rms._v_attrs['window_step'] = step
    rms._v_attrs['window_step_samples'] = window_step
    rms._v_attrs['chunk_samples'] = c_samples
    rms._v_attrs['chunk_loverlap'] = c_loverlap
    rms._v_attrs['new_shape'] = new_shape
    rms._v_attrs['algorithm'] = algorithm

    rms._v_attrs['fc_lowpass'] = channel.filter_freq_lp
    rms._v_attrs['fc_highpass'] = channel.filter_freq_hp
    rms._v_attrs['filter_order'] = channel.filter_order
    rms._v_attrs['filter_btype'] = channel.filter_btype
    rms._v_attrs['filter_padding'] = channel._padding

    rms._v_attrs['diff_mode'] = channel.diff_mode
    rms._v_attrs['differential'] = channel.diff_matrix

    b, a = channel.filter_coefficients
    rms._v_attrs['b_coefficients'] = b
    rms._v_attrs['a_coefficients'] = a

    # These must be here for compatibility with the Channel/MultiChannel classes
    # defined in cns.channel (especially if you use the from_node classmethod).
    rms._v_attrs['fs'] = (window_step/channel.fs)**-1
    rms._v_attrs['channels'] = 16
    rms._v_attrs['t0'] = 0

    if algorithm == 'mean':
        compute_rms = lambda x: np.mean(x**2, axis=-1)**0.5
    elif algorithm == 'median':
        compute_rms = median_std
    else:
        raise ValueError, 'Unknown algorithm "{}"'.format(algorithm)
    

    iterable = chunk_iter(channel, c_samples-c_loverlap, loverlap=c_loverlap)
    for i_chunk, chunk in enumerate(iterable):

        # This is a hack to discard the very last chunk if it's the wrong size.
        # Eventually I need to come up with better logic here ...
        if chunk.shape[-1] != c_samples:
            print 'discarding chunk'
            continue

        ch_stride, s_stride = chunk.strides
        strides = ch_stride, window_step*s_stride, s_stride
        chunk = as_strided(chunk, new_shape, strides)

        # Create an expression to be evaluated using the numexpr package
        #exp = tables.Expr('sum(chunk**2, axis=1)')
        #exp.setOutput(rms)
        #exp.eval()

        result = compute_rms(chunk)
        rms.append(result)

        if progress_callback(i_chunk*c_samples, total_samples, ''):
            aborted = True
            break

def running_rms_old(input_node, output_node, duration, step, processing,
                algorithm='median', progress_callback=None):
    '''
    Compute the running RMS value of the noise floor

    Parameters
    ----------
    input_node : instance of tables.Group
        The PyTables group pointing to the root of the experiment node.  The
        physiology data will be found under input_node/data/physiology/raw.
    output_node : instance of tables.Group
        The target node to save the data to.  Note that this must be an instance
        of tables.Group since several arrays will be saved under the target
        node.
    duration : float (seconds)
        Duration to use for computing each chunk.
    step : float (seconds)
        Step size.  Degree of overlap between chunks.  Smaller step sizes lead
        to a smoother estimate of the RMS; however, this comes at the expense of
        processing time.
    processing : dict
        Dictionary containing settings that will be passed along to
        ProcessedMultiChannel.  These serve as instructions for referencing and
        filtering of the data.  The dictionary must include the following
        elements:
            freq_lp : float (Hz)
                The lowpass frequency
            freq_hp : float (Hz)
                The highpass frequency
            filter_btype : {'bandpass', 'lowpass', 'highpass'}
                Band type.  If lowpass or highpass, the appropriate cutoff
                frequency will be ignored.
            filter_order : int
                The filter order
            bad_channels : array-like
                List of bad channels using 0-based indexing
            diff_mode : ['all good']
                Type of referencing to use.  Currently only one mode
                (referencing against all the good channels) is supported.
    algorithm : {'median', 'mean'}
        Algorithm for computing the 'M' in RMS.  Using the median rather than
        the mean has been recommended by some scientists (e.g. Quiroga et al.,
        2004).
    progress_callback : callable
        Function to be notified each time a chunk is processed.  The function
        must take three arguments, (chunk number, total chunks, message).  As
        each chunk is processed, the function will be called with updates to the
        progress.  If the function returns a nonzero (True) value, the
        processing will terminate.
    '''
    # Make a dummy progress callback if none is requested
    if progress_callback is None:
        progress_callback = lambda x, y, z: False

    raw_node = input_node.data.physiology.raw
    channel = ProcessedFileMultiChannel.from_node(raw_node, **processing)

    c_samples = int(duration*channel.fs)
    c_step = int(step*channel.fs)

    channels, total_samples = raw_node.shape

    # Create the output data node
    fh_out = output_node._v_file
    filters = tables.Filters(complevel=1, complib='zlib', fletcher32=True)
    rms = fh_out.createEArray(output_node, 'rms', raw_node.atom,
                              (channels, 0), filters=filters,
                              title='Running RMS of signal')

    # Save some data about how the RMS was computed

    rms._v_attrs['chunk_duration'] = duration
    rms._v_attrs['chunk_spacing'] = step
    rms._v_attrs['chunk_samples'] = c_samples
    rms._v_attrs['chunk_step'] = c_step
    rms._v_attrs['algorithm'] = algorithm

    rms._v_attrs['fc_lowpass'] = channel.filter_freq_lp
    rms._v_attrs['fc_highpass'] = channel.filter_freq_hp
    rms._v_attrs['filter_order'] = channel.filter_order
    rms._v_attrs['filter_btype'] = channel.filter_btype
    rms._v_attrs['filter_padding'] = channel._padding

    rms._v_attrs['diff_mode'] = channel.diff_mode
    rms._v_attrs['differential'] = channel.diff_matrix

    b, a = channel.filter_coefficients
    rms._v_attrs['b_coefficients'] = b
    rms._v_attrs['a_coefficients'] = a

    rms._v_attrs['fs'] = 1/(c_step*channel.fs)

    if algorithm == 'mean':
        compute_rms = lambda x: np.mean(x**2, axis=1)**0.5
    elif algorithm == 'median':
        compute_rms = median_std
    else:
        raise ValueError, 'Unknown algorithm "{}"'.format(algorithm)

    print c_samples, c_step
    for i_chunk, chunk in enumerate(chunk_iter(channel, c_samples, c_step)):
        rms.append(compute_rms(chunk)[np.newaxis].T)

        if progress_callback(i_chunk*c_step, total_samples, ''):
            aborted = True
            break

def decimate_waveform(input_node, output_node, q=None, N=4, progress_callback=None,
                      chunk_size=default_chunk_size, include_block_data=True):
    '''
    Decimates the waveform data to a lower sampling frequency using a lowpass
    filter cutoff.  

    A 4th order lowpass butterworth filter is used in conjunction with filtfilt
    to apply a zero phase-delay to the waveform.

    This code is carefully designed to handle boundary issues when processing
    large datasets in chunks (e.g. stabilizing the edges of each chunk when
    filtering and extracting the correct samples from each chunk to ensure
    uniform decimation spacing).

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
    q : { None, int }
        The downsampling (i.e. decimation) factor.  If None, q will be set to
        floor(source_fs/600) (i.e. the output sampling frequency will be as
        close to 600 Hz as without being less than 600 Hz). 
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
    include_block_data : boolean
        Copy the information regarding blocks occuring in the experiment (e.g.
        trial timestamps, poke timestamps, trial log, etc.) decimated node file
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
    if q is None:
        q = np.floor(source_fs/600.0)
    target_fs = source_fs/q

    n_channels, n_samples = raw.shape

    fh_out = output_node._v_file
    filters = tables.Filters(complevel=1, complib='zlib', fletcher32=True)
    lfp = fh_out.createEArray(output_node, 'lfp', raw.atom,
                              (n_channels, 0), filters=filters,
                              title="Lowpass filtered signal for LFP analysis")

    # Critical frequency of the lowpass filter (ensure that the filter cutoff is
    # half the target sampling frequency to avoid aliasing).
    Wn = (0.5*target_fs)/(0.5*source_fs)
    b, a = signal.iirfilter(N, Wn, btype='lowpass')

    # Need to consider this in more detail
    b = b.astype(raw.dtype)
    a = a.astype(raw.dtype)
    
    # The number of samples in each chunk *must* be a multiple of the decimation
    # factor so that we can extract the *correct* samples from each chunk.
    c_samples = chunk_samples(raw, chunk_size, q)
    overlap = 3*len(b)
    iterable = chunk_iter(raw, c_samples, loverlap=overlap, roverlap=overlap)

    for i, chunk in enumerate(iterable):
        chunk = signal.filtfilt(b, a, chunk, padlen=0).astype(raw.dtype)
        chunk = chunk[:, overlap:-overlap:q]
        lfp.append(chunk)
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
    lfp._v_attrs['freq_lowpass'] = target_fs*0.5

    # Save some information about where we obtained the raw data from
    filename = path.basename(input_node._v_file.filename)
    output_node._v_attrs['source_file'] = filename
    output_node._v_attrs['source_pathname'] = input_node._v_pathname

    if include_block_data:
        block_node = output_node._v_file.createGroup(output_node, 'block_data')
        copy_block_data(input_node, block_node)

def extract_spikes(input_node, output_node, channels, noise_std, threshold_stds,
                   rej_threshold_stds, processing, window_size=2.1,
                   cross_time=0.5, cov_samples=10000, progress_callback=None,
                   chunk_size=default_chunk_size, include_block_data=True):
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
            diff_mode : ['all good']
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
    include_block_data : boolean
        Copy the information regarding blocks occuring in the experiment (e.g.
        trial timestamps, poke timestamps, trial log, etc.) decimated node file
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
    # filtering (as well as chunking the data).  TODO I'd rather explicitly code
    # the referencing and filtering logic into this function rather than adding
    # a layer of abstraction.
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

    fh_out = output_node._v_file

    # Save some information about where we obtained the raw data from
    filename = str(path.basename(input_node._v_file.filename))
    fh_out.setNodeAttr(output_node, 'source_file', filename)
    fh_out.setNodeAttr(output_node, 'source_pathname', input_node._v_pathname)

    ########################################################################
    # BEGIN EVENT NODE
    ########################################################################

    event_node = fh_out.createGroup(output_node, 'event_data')

    # Ensure that underlying datatype of HDF5 array containing waveforms is
    # identical to the datatype of the source waveform (e.g. 32-bit float).
    # EArrays are a special HDF5 array that can be extended dynamically on-disk
    # along a single dimension.
    size = (0, n_channels, window_samples)
    atom = tables.Atom.from_dtype(node.dtype)
    title = 'Event waveforms (event, channel, sample)'
    fh_waveforms = fh_out.createEArray(event_node, 'waveforms', atom, size,
                                       title=title)
    fh_waveforms._v_attrs['fs'] = fs

    # If we have a sampling rate of 12.5 kHz, storing indices as a 32-bit
    # integer allows us to locate samples in a continuous waveform of up to 49.7
    # hours in duration.  This is more than sufficient for our purpose (we will
    # likely run into file size issues well before this point anyway).
    fh_indices = fh_out.createEArray(event_node, 'timestamps_n',
                                     tables.Int32Atom(), (0,),
                                     title='Event time (cycles)')
    fh_indices._v_attrs['fs'] = fs
    
    # The actual channel the event was detected on.  We can represent up
    # to 32,767 channels with a 16 bit integer.  This should be
    # sufficient for at least the next year.
    fh_channels = fh_out.createEArray(event_node, 'channels',
                                      tables.Int16Atom(), (0,),
                                      title='Event channel (1-based)')

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
    fh_channel_indices = fh_out.createEArray(event_node, 'channel_indices',
                                             tables.Int16Atom(), (0,))

    # We can represent up to 256 values with an 8 bit integer.  That's overkill
    # for a boolean datatype; however Matlab doesn't support pure boolean
    # datatypes in a HDF5 file.  Lame.  Artifacts is a 2d array of [event,
    # channel] indicating, for each event, which channels exceeded the artifact
    # reject threshold.
    size = (0, n_channels)
    fh_artifacts = fh_out.createEArray(event_node, 'artifacts',
                                       tables.Int8Atom(), size,
                                       title='Artifact (event, channel)')

    # Since we conventionally count channels from 1, convert our 0-based index
    # to a 1-based index.  It's OK to set these as node attributes becasue they
    # will never be empty arrays.  However, let's keep consistency and make
    # everything that's an array an array.
    fh_out.setNodeAttr(event_node, 'extracted_channels', channels+1)
    fh_out.setNodeAttr(event_node, 'noise_std', noise_std)
    fh_out.setNodeAttr(event_node, 'chunk_samples', c_samples)
    fh_out.setNodeAttr(event_node, 'chunk_loverlap', loverlap)
    fh_out.setNodeAttr(event_node, 'chunk_roverlap', roverlap)
    fh_out.setNodeAttr(event_node, 'window_size', window_size)
    fh_out.setNodeAttr(event_node, 'cross_time', cross_time)
    fh_out.setNodeAttr(event_node, 'samples_before', samples_before)
    fh_out.setNodeAttr(event_node, 'samples_after', samples_after)
    fh_out.setNodeAttr(event_node, 'window_samples', window_samples)
    fh_out.setNodeAttr(event_node, 'threshold', thresholds)
    fh_out.setNodeAttr(event_node, 'reject_threshold', rej_thresholds)
    fh_out.setNodeAttr(event_node, 'threshold_std', threshold_stds)
    fh_out.setNodeAttr(event_node, 'reject_threshold_std', rej_threshold_stds)

    ########################################################################
    # END EVENT NODE
    ########################################################################

    ########################################################################
    # BEGIN FILTER NODE
    ########################################################################
    filter_node = fh_out.createGroup(output_node, 'filter')

    # This needs to be an EArray rather than an attribute or typical Array
    # because setNodeAttr() and createArray complain if you attempt to pass an
    # empty array to it (I think this is actually an implementation issue with
    # the underlying HDF5 library).  By doing this workaround, we can ensure
    # that empty arrays (i.e. no bad channels) can also be saved.
    fh_bad_channels = fh_out.createEArray(filter_node, 'bad_channels',
                                          tables.Int8Atom(), (0,))
    fh_bad_channels.append(np.array(node.bad_channels)+1)

    # Currently we only support one referencing mode (i.e. reference against the
    # average of the good channels) so I've hardcoded this attribute for now.
    fh_out.setNodeAttr(filter_node, 'diff_mode', node.diff_mode)
    fh_out.createArray(filter_node, 'differential', node.diff_matrix)

    # Be sure to save the filter coefficients used (not sure if this is
    # meaningful).  The ZPK may be more useful in general.  Unfortunately, HDF5
    # does not natively support complex numbers and I'm not inclined to deal
    # with the issue at present.
    fh_out.setNodeAttr(filter_node, 'fc_lowpass', node.filter_freq_lp)
    fh_out.setNodeAttr(filter_node, 'fc_highpass', node.filter_freq_hp)
    fh_out.setNodeAttr(filter_node, 'filter_order', node.filter_order)
    fh_out.setNodeAttr(filter_node, 'filter_btype', node.filter_btype)
    fh_out.setNodeAttr(filter_node, 'filter_padding', node._padding)

    b, a = node.filter_coefficients
    fh_out.createArray(filter_node, 'b_coefficients', b)
    fh_out.createArray(filter_node, 'a_coefficients', a)

    ########################################################################
    # END FILTER NODE
    ########################################################################

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

    # Keep the user updated as to how many candidate spikes they're getting
    tot_features = 0

    iterable = chunk_iter(node, c_samples, loverlap, roverlap,
                          ndslice=np.s_[channels, :])

    aborted = False
    samples_processed = 0

    t_chunk_start = time.time()
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

        n_features = len(sample_index)
        tot_features += n_features

        # This may not be the most efficient approach, but it suffices.
        for s in sample_index:
            fh_waveforms.append(chunk[..., s:s+window_samples][np.newaxis])

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

        # Track the total number of samples processed.  For the first n-1
        # blocks, this will be equivalent to i_chunk*c_samples.  However, the
        # size of the last chunk will be variable since it's highly unlikely
        # that the total number of samples will be an integer multiple of
        # c_samples.
        samples_processed += chunk.shape[-1]

        # Update the progress callback each time we finish processing a chunk.
        # If the progress callback returns True, end the processing immediately.
        # Be sure to add a note to the output node indicating that acquisition
        # was aborted.
        mesg = 'Found {} features'.format(tot_features)
        if progress_callback(i_chunk*c_samples, total_samples, mesg):
            aborted = True
            break

    # Save some informationa bout whet
    output_node._v_attrs['aborted'] = aborted
    output_node._v_attrs['last_processed_sample'] = samples_processed
        
    t_chunk_end = time.time()
    t_chunk = t_chunk_end-t_chunk_start
    log.debug('Extracting spikes took {} seconds'.format(t_chunk))

    # Find all the artifacts.  First, check the entire waveform array to see if
    # the signal exceeds the artifact threshold defined on any given sample.
    # Note that the specified reject threshold for each channel will be honored
    # via broadcasting of the array.  This uses tables.Expr to avoid creating
    # large Numpy temporary arrays in memory (and should be much faster). 
    rej_thresholds = rej_thresholds[np.newaxis].T
    exp = tables.Expr("(fh_waveforms >= rej_thresholds) |" 
                      "(fh_waveforms < -rej_thresholds)")

    # Now, evaluate and reduce the expression so that we end up with a 2d array
    # [event, channel] indicating whether the waveform for any given event
    # exceed the reject threshold specified for that channel.
    artifacts = np.any(exp.eval(), axis=-1)
    fh_artifacts.append(artifacts)

    # If the user explicitly requested a cancel, compute the covariance matrix
    # only on the samples we were able to draw from the data.
    cov_waves = cov_waves[:cov_i]

    # Compute the covariance matrix in the format required by UltraMegaSort2000
    # (note by Brad -- I don't fully understand how the covariance matrix is
    # used by UMS2000; however, I spoke with the author and he indicated this is
    # the correct format for the matrix).
    cov_waves.shape = cov_i, -1
    cov_matrix = np.cov(cov_waves.T)
    fh_out.createArray(event_node, 'covariance_matrix', cov_matrix)
    fh_out.createArray(event_node, 'covariance_data', cov_waves)

    # Convert the timestamp indices to seconds and save in an array called
    # timestamps
    timestamps = fh_indices[:].astype('f')/fs
    fh_out.createArray(event_node, 'timestamps', timestamps,
                       title='Event time (sec)')

    if include_block_data:
        block_node = output_node._v_file.createGroup(output_node, 'block_data')
        copy_block_data(input_node, block_node)

    # Notify the progress dialog that we're done
    progress_callback(total_samples, total_samples, 'Complete')
