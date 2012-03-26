'''
Collection of utilities to aid in generating (beautiful) plots
'''
from __future__ import division

import pylab
import numpy as np

def color_iterator(grouping, cmap='jet'):
    '''
    Given a Matplotlib colormap, iterate through the color range in equal-sized
    increments.
    '''
    n = len(grouping)
    if isinstance(cmap, basestring):
        cmap = pylab.get_cmap(cmap)
    for i, g in enumerate(grouping):
        if n == 1:
            yield cmap(1), g
        else:
            yield cmap(i/(n-1)), g

def adjust_spines(ax, spines, position=5):
    for loc, spine in ax.spines.iteritems():
        if loc in spines:
            spine.set_position(('outward', position)) # outward by 10 points
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

def best_rowscols(n):
    '''
    Compute the best number of rows and cols to generate a semi-square or
    rectangular layout of subplots given the number of plots being generated.
    '''
    n_square = n**0.5
    n_rows = np.round(n_square)
    n_cols = np.ceil(n_square)
    return n_rows, n_cols

class AxesIterator(object):
    '''
    Parameters
    ----------
    extra
        Number of extra plots, in addition to len(groups), to reserve axes for
        when computing the optimal row/column layout
    sharex
        If True, share the x-axis between axes
    sharey
        If True, share the y-axis between axes
    adjust_spines
        If True, adjust spines using Brad's preferred axes style
    max_groups
        Maximum number of axes per figure. A new figure will be generated each
        time the axes reaches the maximum.  If set to infinity, all axes will be
        squeezed onto a single figure (even if there's a million of them).

    sharex and sharey are attributes that can be modified at any time during
    iteration to change the sharing behavior.
    '''

    def __init__(self, groups, extra=0, sharex=True, sharey=True,
                 max_groups=np.inf):
        self.sharex = sharex
        self.sharey = sharey
        self.groups = groups
        self.group_iter = iter(groups)
        self.max_groups = max_groups
        self.n_groups = min(len(self.groups)+extra, self.max_groups)
        self.n_rows, self.n_cols = best_rowscols(self.n_groups)
        self.i = 0
        self.current_axes = None
        self.figures = []

    def __iter__(self):
        return self

    def next(self):
        # When the call to group_iter.next() raises a StopIteration exception,
        # this exception must also bubble up and terminate this generator as
        # well.  We call group_iter.next() at the very beginning as a check to
        # make sure we have not reached the end of the sequence before adding
        # the new plot to the graph.
        g = self.group_iter.next()

        if self.i == 0:
            self.current_figure = pylab.figure()
            self.figures.append(self.current_figure)
        self.i = (self.i + 1) % self.max_groups

        kw = {}
        if self.sharex:
            kw['sharex'] = self.current_axes
        if self.sharey:
            kw['sharey'] = self.current_axes
        ax = self.current_figure.add_subplot(self.n_rows, self.n_cols, self.i,
                                             **kw)
        self.current_axes = ax

        if adjust_spines:
            firstcol = (self.i % self.n_cols) == 1
            lastrow = self.i > (self.n_cols*(self.n_rows-1))
            if firstcol and lastrow:
                adjust_spines(self.current_axes, ('bottom', 'left'))
            elif firstcol:
                adjust_spines(self.current_axes, ('left'))
            elif lastrow:
                adjust_spines(self.current_axes, ('bottom'))
            else:
                adjust_spines(self.current_axes, ())
        return self.current_axes, g
    
def figure_generator(max_groups):
    i = 0
    rows, cols = best_rowscols(max_groups)
    while True:
        if i == 0:
            figure = pylab.figure()
        ax = figure.add_subplot(rows, cols, i+1)
        adjust_spines(ax, ('bottom', 'left'))
        yield ax
        i = (i + 1) % max_groups
