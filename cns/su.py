'''
Collection of functions for computing statistics on a spike train

Most of these functions are optimized for memory-usage and speed; however these
optimizations assume certain constraints on the data (e.g.  the spike times
often must be sorted).  Be sure to see the docstring for each function.

Most functions don't require a particular unit (i.e. msec or seconds).  The
assumption is that all arguments provided will be of the same unit.  That is, if
you specify `durations` in seconds, then the `et` (event times) and `tt`
(trigger times) should be specified in seconds as well.  This approach gives you
flexibility in handling data in the units (and datatype) that make the most
sense for your analysis.

The following variable naming conventions are found throughout the functions in
this module:

tt : trigger times
    Times to compute the metric against (e.g. peri-stimulus times, etc.).  This
    is typically the trigger time of the event in question (e.g. poke onset,
    trial start, etc.).
et : event times
    Time of the events (typically the spikes)
    
'''
from __future__ import division

import numpy as np
import numexpr as ne
import scipy as sp
from .util.binary_funcs import epochs_contain, smooth_epochs

def rates(et, tt, offsets, durations, censored=None, squeeze=False):
    '''
    Compute the rate of `et` for each trigger time specified in `tt` given the
    list of `offsets` and `durations`.  

    Assumes that et and tt have already been sorted (the algorithm will produce
    incorrect results otherwise).  This is optimized for speed (so far as we can
    achieve via Python/Numpy) using searchsorted.

    Parameters
    ----------
    censored : 2D array of epochs

    Returns
    -------
    3D array (tt, offset, duration)
    '''
    tt = np.array(tt)[..., np.newaxis, np.newaxis]
    offsets = np.array(offsets)[..., np.newaxis]
    durations = np.array(durations)

    # Use broadcasting to create the lower/upper bound of the rate windows we
    # want to compute rate for.  The difference between ub_i and lb_i tells us
    # how many spikes were in that window.
    lb = tt + offsets
    ub = tt + offsets + durations
    lb_i = np.searchsorted(et, lb)
    ub_i = np.searchsorted(et, ub)
    num_indices = ub_i-lb_i

    # Now, normalize by the duration to get the actual rate for that given trial
    result = num_indices.astype('f')/durations

    # Finally, check to see which combinations of parameters are invalid due to
    # the lower/upper bounds selected and set the computed rate for those to
    # NaN.
    if censored is not None:
        invalid = epochs_contain(censored, lb) | epochs_contain(censored, ub)
        result[invalid] = np.nan

    # Remove singleton dimensions if requested
    if squeeze:
        result = result.squeeze()

    return result

def rossum_distance(smoothed):
    '''
    Compute pair-wise rossum distance between the smoothed trains (see
    `smoothed_train`) given a MxN matrix, `smoothed`.

    Result *must* be normalized by vector density and smoothing time constant.

    Uses numexpr to streamline memory usage and speed when processing large
    arrays. 
    '''
    a = smoothed[np.newaxis,:,:]
    b = smoothed[:,np.newaxis,:]
    return ne.evaluate('sum((a-b)**2, axis=2)')

def smoothed_train(et, tt, offset, duration, density=0.001, tau=0.01):
    '''
    Return the spike train extracted at [offset, offset+duration) smoothed by an
    exponential window with time constant given by `tau`.
    '''
    tt = np.array(tt)
    lb = tt + offset
    ub = tt + offset + duration
    lb_i = np.searchsorted(et, lb)
    ub_i = np.searchsorted(et, ub)
    pst = [et[i:j]-t for i,j,t in zip(lb_i, ub_i, tt)]

    samples = int(duration/density)
    vector = np.zeros((len(pst), samples))
    for v, p in zip(vector, pst):
        i = (p-offset)/density
        i = i[i<samples]
        v[i.astype('i')] = 1

    t = np.arange(0, tau*10, density)
    window = (t/tau)*np.exp(-t/tau)
    return sp.signal.lfilter(window, 1, vector, axis=1)

def pst(et, tt, lb, ub):
    '''
    Fast method for computing peri-trigger spike times
    '''
    tt_lb = np.searchsorted(et, tt+lb)
    tt_ub = np.searchsorted(et, tt+ub)
    return [et[lb:ub]-tt for tt, lb, ub in zip(tt, tt_lb, tt_ub)]

def histogram(et, tt, bin_width, lb, ub, censored=None):
    '''
    Fast version of the histogram function that assumes et and tt are sorted
    '''
    if censored is not None:
        mask = epochs_contain(censored, tt+lb) | epochs_contain(censored, tt+ub)
        tt = tt[~mask]
    if len(tt) == 0:
        raise ValueError, 'No trials to compute histogram on'
    pst_times = np.concatenate(pst(et, tt, lb, ub))
    bins = histogram_bins(bin_width, lb, ub)
    n = np.histogram(pst_times, bins=bins)[0]
    return bins[:-1], n/bin_width/len(tt)

def fano_factor(et, tt, bin_width, lb, ub):
    bins = histogram_bins(bin_width, lb, ub)
    histograms = [np.histogram(p, bins=bins)[0] for p in pst(et, tt, lb, ub)]
    histograms = np.c_[histograms]
    return histograms.var(0)/histograms.mean(0)

def histogram_bins(bin_width, lb, ub):
    '''
    Compute bins
    
    Numpy, Scipy and Matplotlib (Pylab) all come with histogram functions, but
    the autogeneration of the bins rarely are what we want them to be.  This
    makes sure that we get the bins we want given the temporal bounds of the
    analysis window (lb, ub) and the bin width.
    '''
    bins =  np.arange(lb, ub, bin_width)
    bins -= bins[np.argmin(np.abs(bins))]
    return bins

def interepoch_times(epochs, n=1000, padding=1, duration=0.1, seed=1321132):
    '''
    Returns a list of inter-epoch times of `duration` that do not occur within
    `padding` of the requested epochs.

    Example
    -------
    >>> from cns import io
    >>> censored = io.load_censored_epochs(ext_filename, channels)
    >>> task = io.load_task_epochs(raw_filename)
    >>> epochs = np.r_[censored, task]
    >>> timestamps = interepoch_times(epochs)

    Does not make an effort to ensure that the random windows are uniformly
    distributed and non-overlapping with themselves.
    '''
    random = np.random.RandomState(seed=seed)
    epochs = smooth_epochs(epochs)
    mask = np.all(np.isfinite(epochs), 1)
    lb, ub = epochs[mask,0][0], epochs[mask,1][-1]

    random_ts = []
    while len(random_ts) < n:
        # We actually attempt to compute all the random times in one fell swoop
        # by generating 2x the random numbers, then checking to see how many of
        # these random numbers impinge on the epochs.  If we don't have enough
        # left after filtering out the impinging timestamps, then we keep
        # trying.
        x = random.uniform(low=lb, high=ub, size=n*2)
        mask = epochs_contain(epochs, x) | epochs_contain(epochs, x+duration)
        random_ts.extend(x[~mask])
    return np.array(random_ts)[:n]

