from __future__ import division
import sys
import re
from glob import glob
from os import path
import subprocess

from scipy.stats import norm

from pandas import DataFrame
import numpy as np
import tables
import pylab
import matplotlib as mp
from matplotlib.transforms import blended_transform_factory
import pypsignifit as psi

from cns.plottools import AxesIterator, adjust_spines

mp.rcParams['figure.facecolor'] = 'white'
mp.rcParams['figure.figsize'] = 11, 8.5
mp.rcParams['figure.subplot.wspace'] = 0.4
mp.rcParams['font.size'] = 7
mp.rcParams['axes.titlesize'] = 10
mp.rcParams['axes.labelsize'] = 8
mp.rcParams['xtick.direction'] = 'out'
mp.rcParams['xtick.labelsize'] = 6
mp.rcParams['xtick.major.size'] = 2
mp.rcParams['xtick.major.pad'] = 2
mp.rcParams['ytick.direction'] = 'out'
mp.rcParams['ytick.labelsize'] = 6
mp.rcParams['ytick.major.size'] = 2
mp.rcParams['ytick.major.pad'] = 2

def csc(et, tt, trial_ub, trial_lb):
    '''
    Generates cumulutaive spike count plots.

    Parameters
    ----------
    et : array-like
        event times (i.e. spike times)
    tt : array-like
        trigger times (i.e. to reference event times to)
    trial_lb : scalar
        lower bound of plot (start counting from this point)
    trial_ub : scalar
        upper bound of plot
    '''
    i = 0
    for t in tt:
        mask = (et <= (t-trial_lb)) & (et > (t+trial_ub))
        pst = et[mask] - t

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

def import_spikes(filename, channel, artifact_reject=True,
                  include_behavior_data=True):
    with tables.openFile(filename, 'r') as fh:
        mask = fh.root.channels[:] == channel
        mask = fh.root.artifacts[channel]
        return fh.root.timestamps[mask], fh.root._v_attrs['fs']

def generate_histogram2(filename, channel, trial_ub=None):
    with tables.openFile(filename, 'r') as fh:
        ch_mask = fh.root.channels[:] == channel
        et = fh.root.timestamps[ch_mask]
        fs = fh.root._v_attrs['fs']
        trial_log = DataFrame(fh.root.trial_log[:trial_ub])
        trial_log['tt'] = fh.root.physiology_epoch[:trial_ub,0]
        trial_log = trial_log[trial_log['ttype'] != 'GO_REMIND']
        trial_log['yes'] = trial_log['response'] == 'spout'

        bin_width = int(0.016*fs)
        lb = int(-2*fs)
        ub = int(4*fs)
        bins = histogram_bins(bin_width, lb, ub)

        rate_start = np.argmin(np.abs(bins))
        rate_bins = 8

        figures = []
        for (speaker, duration), frame in trial_log.groupby(('speaker', 'duration')):
            levels, rates = [], []
            figure = pylab.figure()
            figures.append((speaker, duration, figure))

            # Title the figure
            basename = path.basename(filename)
            title_fmt = '{} msec ({}) :: Channel {} ({})'
            title = title_fmt.format(int(duration*1e3), speaker, channel,
                                     basename)
            figure.suptitle(title)

            iterator = AxesIterator(frame.groupby('level'), extra=3)
            for ax, (level, sf) in iterator:
                # There are probably far more efficient ways to compute the
                # histogram, but taking advantage of broadcasting suffices.
                tt = sf['tt'].values
                pst = et-tt[np.newaxis].T
                pst = pst[(pst >= lb) & (pst < ub)]

                n = np.histogram(pst, bins=bins)[0]
                n = n/bin_width/len(tt)*fs

                # Do this first so the rectangle appears on the bottom below the
                # data plots
                t = blended_transform_factory(ax.transData, ax.transAxes)
                ax.fill_between([0, 0, duration, duration], [0, 1, 1, 0],
                                color='0.75', transform=t)

                ax.bar(bins[:-1]/fs, n, bin_width/fs, color='k', linewidth=0.5)
                ax.set_title('{} (n={})'.format(level, len(tt)))

                ax.yaxis.grid(True)
                levels.append(level)
                rates.append(np.mean(n[rate_start:rate_start+rate_bins]))

            ax.axis(xmin=-2, xmax=4, ymin=0)

            # Compute the psychometric function here ... 
            aggfuncs = {'p': 'mean', 'n': 'count'}
            yes = frame.groupby('level')['yes'].agg(aggfuncs)
            clip_value = 0.5*np.min(yes['n'])**-1
            p_yes = yes['p'].clip(clip_value, 1-clip_value)
            zscore = p_yes.apply(norm.ppf)
            dprime = zscore.ix[1:] - zscore.ix[0]

            # Curve fit the percent yes function
            levels = yes.index.values
            psi_data = np.c_[levels, yes['p'], yes['n']]
            priors = ("unconstrained", "unconstrained", "Beta(1,1)",
                      "Beta(1,1)")
            bi = psi.BayesInference(psi_data, nafc=1, priors=priors,
                                    maxnsamples=1000)
            fitted_levels = np.arange(np.min(levels)-5, np.max(levels)+5, 1)
            fitted_p_yes = np.clip(bi.evaluate(fitted_levels), clip_value,
                                   1-clip_value)
            fitted_fa = np.clip(bi.evaluate(-20), clip_value, 1-clip_value)
            fitted_dprime = norm.ppf(fitted_p_yes) - norm.ppf(fitted_fa)
            fitted_th = np.interp(1, fitted_dprime, fitted_levels)

            # Get the next axes in the sequence and plot it
            ax = pylab.subplot(iterator.n_rows, iterator.n_cols, iterator.i+1)
            adjust_spines(ax, ('bottom', 'left'))
            ax.plot(dprime.index, dprime.values, 'ko')
            ax.plot(fitted_levels, fitted_dprime, 'r-')
            ax.plot([fitted_th], [1], 'go')
            ax.set_xlabel('Level (dB SPL)')
            ax.set_ylabel('d\'')
            ax.grid(True)

            ax = pylab.subplot(iterator.n_rows, iterator.n_cols, iterator.i+2)
            adjust_spines(ax, ('bottom', 'left'))
            ax.plot(levels, rates, 'ko-')
            ax.axvline(fitted_th, c='g')
            ax.set_xlabel('Level (dB SPL)')
            ax.set_ylabel('Rate (sp/sec)')
            ax.grid(True)

            ax = pylab.subplot(iterator.n_rows, iterator.n_cols, iterator.i+3)
            adjust_spines(ax, ('bottom', 'left'))
            ch_index = np.flatnonzero(fh.root.extracted_channels[:] == \
                                      channel)[0]
            waveforms = fh.root.waveforms[:,ch_index,:][ch_mask] * 1e3
            mean_waveform = waveforms.mean(0).T
            std_waveform = waveforms.std(0).T
            t = np.arange(len(mean_waveform))/fs*1e3
            ax.plot(t, mean_waveform, 'k-')
            ax.fill_between(t, mean_waveform+std_waveform,
                            mean_waveform-std_waveform, color='0.75')
            ax.set_xlim(0, t.max())

        return figures

def generate_histogram(filename, channel, trial_ub=None):
    with tables.openFile(filename, 'r') as fh:
        ch_mask = fh.root.channels[:] == channel
        et = fh.root.timestamps[ch_mask]
        fs = fh.root._v_attrs['fs']
        trial_log = DataFrame(fh.root.trial_log[:trial_ub])
        trial_log['tt'] = fh.root.physiology_epoch[:trial_ub,0]
        trial_log = trial_log[trial_log['ttype'] != 'GO_REMIND']
        trial_log['yes'] = trial_log['response'] == 'spout'

        bin_width = int(0.016*fs)
        lb = int(-2*fs)
        ub = int(4*fs)
        bins = histogram_bins(bin_width, lb, ub)

        rate_start = np.argmin(np.abs(bins))
        rate_bins = 8

        figures = []
        for (speaker, duration), frame in trial_log.groupby(('speaker', 'duration')):
            levels, rates = [], []
            figure = pylab.figure()
            figures.append((speaker, duration, figure))

            # Title the figure
            basename = path.basename(filename)
            title_fmt = '{} msec ({}) :: Channel {} ({})'
            title = title_fmt.format(int(duration*1e3), speaker, channel,
                                     basename)
            figure.suptitle(title)

            iterator = AxesIterator(frame.groupby('level'), extra=3)
            for ax, (level, sf) in iterator:
                # There are probably far more efficient ways to compute the
                # histogram, but taking advantage of broadcasting suffices.
                tt = sf['tt'].values
                pst = et-tt[np.newaxis].T
                pst = pst[(pst >= lb) & (pst < ub)]

                n = np.histogram(pst, bins=bins)[0]
                n = n/bin_width/len(tt)*fs

                # Do this first so the rectangle appears on the bottom below the
                # data plots
                t = blended_transform_factory(ax.transData, ax.transAxes)
                ax.fill_between([0, 0, duration, duration], [0, 1, 1, 0],
                                color='0.75', transform=t)

                ax.bar(bins[:-1]/fs, n, bin_width/fs, color='k', linewidth=0.5)
                ax.set_title('{} (n={})'.format(level, len(tt)))

                ax.yaxis.grid(True)
                levels.append(level)
                rates.append(np.mean(n[rate_start:rate_start+rate_bins]))

            ax.axis(xmin=-2, xmax=4, ymin=0)

            # Compute the psychometric function here ... 
            aggfuncs = {'p': 'mean', 'n': 'count'}
            yes = frame.groupby('level')['yes'].agg(aggfuncs)
            clip_value = 0.5*np.min(yes['n'])**-1
            p_yes = yes['p'].clip(clip_value, 1-clip_value)
            zscore = p_yes.apply(norm.ppf)
            dprime = zscore.ix[1:] - zscore.ix[0]

            # Curve fit the percent yes function
            levels = yes.index.values
            psi_data = np.c_[levels, yes['p'], yes['n']]
            priors = ("unconstrained", "unconstrained", "Beta(1,1)",
                      "Beta(1,1)")
            bi = psi.BayesInference(psi_data, nafc=1, priors=priors,
                                    maxnsamples=1000)
            fitted_levels = np.arange(np.min(levels)-5, np.max(levels)+5, 1)
            fitted_p_yes = np.clip(bi.evaluate(fitted_levels), clip_value,
                                   1-clip_value)
            fitted_fa = np.clip(bi.evaluate(-20), clip_value, 1-clip_value)
            fitted_dprime = norm.ppf(fitted_p_yes) - norm.ppf(fitted_fa)
            fitted_th = np.interp(1, fitted_dprime, fitted_levels)

            # Get the next axes in the sequence and plot it
            ax = pylab.subplot(iterator.n_rows, iterator.n_cols, iterator.i+1)
            adjust_spines(ax, ('bottom', 'left'))
            ax.plot(dprime.index, dprime.values, 'ko')
            ax.plot(fitted_levels, fitted_dprime, 'r-')
            ax.plot([fitted_th], [1], 'go')
            ax.set_xlabel('Level (dB SPL)')
            ax.set_ylabel('d\'')
            ax.grid(True)

            ax = pylab.subplot(iterator.n_rows, iterator.n_cols, iterator.i+2)
            adjust_spines(ax, ('bottom', 'left'))
            ax.plot(levels, rates, 'ko-')
            ax.axvline(fitted_th, c='g')
            ax.set_xlabel('Level (dB SPL)')
            ax.set_ylabel('Rate (sp/sec)')
            ax.grid(True)

            ax = pylab.subplot(iterator.n_rows, iterator.n_cols, iterator.i+3)
            adjust_spines(ax, ('bottom', 'left'))
            ch_index = np.flatnonzero(fh.root.extracted_channels[:] == \
                                      channel)[0]
            waveforms = fh.root.waveforms[:,ch_index,:][ch_mask] * 1e3
            mean_waveform = waveforms.mean(0).T
            std_waveform = waveforms.std(0).T
            t = np.arange(len(mean_waveform))/fs*1e3
            ax.plot(t, mean_waveform, 'k-')
            ax.fill_between(t, mean_waveform+std_waveform,
                            mean_waveform-std_waveform, color='0.75')
            ax.set_xlim(0, t.max())

        return figures

if __name__ == '__main__':
    # Notes on special cases
    # 110122_G4_tail_behavior.hd5 - only first 137 trials are valid
    # 110123_G1_fluffy_behavior.hd5 - Two spurious triggers at end of
    # physiology/ts that need to be discarded.  First 296 are valid and
    # correlate with data stored in trial_log.
    # 111205_G4_tail_behavior_extracted_v2.hd5 - First 120 trials valid
    def _generate_histogram(filename, channel):
        figures = generate_histogram(filename, channel)
        filename = re.sub(r'(.*)\.(h5|hd5|hdf5)',
                          r'\1_hist_{}_'.format(channel),
                          filename)
        for speaker, duration, figure in figures: 
            ext = '{}_{}ms.png'.format(speaker, int(duration*1000))
            figure.savefig(filename+ext)
            print 'saved to {}'.format(filename+ext)

    def _process_file(filename):
        with tables.openFile(filename) as fh:
            channels = fh.root.extracted_channels[:]
        for channel in channels:
            _generate_histogram(filename, channel)
            # Be sure to close the figures after we've saved them to a file
            # otherwise we'll run out of memory!  Hmm... this is not working.
            # Still get out of memory errors.
            pylab.close('all')

    if len(sys.argv) == 2:
        filename = sys.argv[1]
        if filename.endswith('hd5'):
            _process_file(filename)
            pylab.show()
        else:
            pattern = path.join(filename, '*_extracted.hd5')
            for filename in glob(pattern):
                args = "python generate_histogram.py {}".format(filename)
                process = subprocess.Popen(args)
                process.wait()
    else:
        filename, channel = sys.argv[1:]
        channel = int(channel)
        _generate_histogram(filename, channel)
        pylab.show()
