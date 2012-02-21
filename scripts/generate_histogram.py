from __future__ import division
from pandas import DataFrame
import numpy as np
import tables
import pylab


import matplotlib as mp

mp.rcParams['figure.facecolor'] = 'white'
mp.rcParams['axes.grid'] = True
mp.rcParams['font.size'] = 8
mp.rcParams['xtick.labelsize'] = 8
mp.rcParams['ytick.labelsize'] = 8

def adjust_spines(ax, spines, position=10):
    for loc, spine in ax.spines.iteritems():
        if loc in spines:
            spine.set_position(('outward', position)) # outward by 10 points
            #spine.set_smart_bounds(True)
        else:
            spine.set_color('none') # don't draw spine

    # turn off ticks where there is no spine
    if 'left' in spines:
        ax.yaxis.set_ticks_position('left')
    else:
        # No yaxis ticks.  The traditional way of turning off the ticklabels for
        # a given axis is to use setp(ax2, yticklabels=[]); however, this will
        # affect all of the plots that share the same axes.  Instead, use the
        # following trick.
        pylab.setp(ax.get_yticklabels(), visible=False)
        pylab.setp(ax.get_yticklines(), visible=False)

    if 'bottom' in spines:
        ax.xaxis.set_ticks_position('bottom')
    else:
        # no xaxis ticks
        pylab.setp(ax.get_xticklabels(), visible=False)
        pylab.setp(ax.get_xticklines(), visible=False)

def axes_iterator(groups):
    '''
    Given a group of arbitrary size, estimate the optimal arrangement of rows
    and columns to achive a a grid layout of subplots.  Will return both the
    axes subplot along with the group

    Axes will be shared
    '''
    # N     N^0.5   R   C
    # 1     1       1   1
    # 2     1.41    1   2
    # 3     1.73    2   2
    # 4     2       2   2
    # 5     2.23    2   3
    # 6     2.44    2   3
    # 7     2.64    3   3
    # 8     2.82    3   3
    # 9     3       3   3
    n_groups = len(list(groups))
    n_square = n_groups**0.5
    n_rows = np.round(n_square)
    n_cols = np.ceil(n_square)

    i = 0
    for g in groups:
        i += 1
        try:
            axes = pylab.subplot(n_rows, n_cols, i, sharex=axes, sharey=axes)
        except:
            axes = pylab.subplot(n_rows, n_cols, i)

        firstcol = (i % n_cols) == 1
        lastrow = i > (n_cols*(n_rows-1))

        if firstcol and lastrow:
            adjust_spines(axes, ('bottom', 'left'))
        elif firstcol:
            adjust_spines(axes, ('left'))
        elif lastrow:
            adjust_spines(axes, ('bottom'))
        else:
            adjust_spines(axes, ())

        yield axes, g

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
        index
        mask = fh.root.channels[:] == channel
        mask = fh.root.artifacts[channel]
        return fh.root.timestamps[mask], fh.root._v_attrs['fs']

def generate_histogram(filename, channel):
    with tables.openFile(filename, 'r') as fh:
        mask = fh.root.channels[:] == channel
        et = fh.root.timestamps[mask]
        fs = fh.root._v_attrs['fs']
        trial_log = DataFrame(fh.root.trial_log.read())
        trial_log['tt'] = fh.root.physiology_epoch[:,0]
        trial_log = trial_log[trial_log['ttype'] != 'GO_REMIND']

        bin_width = int(0.016*fs)
        lb = int(-2*fs)
        ub = int(4*fs)
        bins = histogram_bins(bin_width, lb, ub)

        figures = []
        for duration, frame in trial_log.groupby('duration'):
            figures.append((duration, pylab.figure()))
            for ax, (level, sf) in axes_iterator(frame.groupby('level')):
                tt = sf['tt'].values
                pst = et-tt[np.newaxis].T
                pst = pst[(pst >= lb) & (pst < ub)]

                n = np.histogram(pst, bins=bins)[0]
                n = n/bin_width/len(tt)*fs
                ax.bar(bins[:-1]/fs, n, bin_width/fs, color='k', linewidth=0)
                ax.set_title('{}: {} (n={})'.format(int(duration*1e3), level, len(tt)))
            ax.set_xlim(-2, 4)
        return figures

#def generate_raster(filename, channel):
#    with tables.openFile(filename, 'r') as fh:
#        mask = fh.root.channels[:] == channel
#        et = fh.root.timestamps[mask]
#        fs = fh.root._v_attrs['fs']
#        trial_log = DataFrame(fh.root.trial_log.read())
#        trial_log['tt'] = fh.root.physiology_epoch[0,:]
#        trial_log = trial_log[trial_log['ttype'] != 'GO_REMIND']
#
#        bin_width = 0.128
#        bins = histogram_bins(int(bin_width*fs), int(-1*fs), int(2*fs))
#
#        for ax, (level, subframe) in axes_iterator(trial_log.groupby('level')):
#            tt = subframe['physiology_tt'].values
#            pst = et-tt[np.newaxis].T
#            pst = pst[(pst >= -1) & (pst < 2)]
#            n = histogram(pst, bins)[0]
#
#            ax.plot(pst, np.arange(len(pst)), '.')
#            ax.set_title('{} (n={})'.format(level, len(tt)))
#            break
#        ax.set_xlim(-1, 2)
#        pylab.show()

if __name__ == '__main__':
    import sys, re
    filename, channel = sys.argv[1:]
    figures = generate_histogram(filename, int(channel))
    filename = re.sub(r'(.*)\.(h5|hd5|hdf5)',
                      r'\1_hist_{}_'.format(channel),
                      filename)
    for duration, figure in figures: 
        ext = '{}ms.png'.format(int(duration*1000))
        figure.savefig(filename+ext)
        print 'saved to {}'.format(filename+ext)
    pylab.show()
