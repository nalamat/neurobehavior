'''
Collection of utilities to aid in generating (beautiful) plots
'''
from __future__ import division

import pylab
import numpy as np
import matplotlib as mp

def log_axis(ax, which='both'):
    if which in ['x', 'both']:
        ax.set_xscale('log')
        ax.xaxis.set_major_formatter(mp.ticker.FormatStrFormatter('%g'))
    if which in ['y', 'both']:
        ax.set_yscale('log')
        ax.yaxis.set_major_formatter(mp.ticker.FormatStrFormatter('%g'))


def add_panel_id(ax, id, fontweight='bold', fontsize='xx-large'):
    ax.text(-0.1, 1.05, str(id), transform=ax.transAxes, fontweight=fontweight,
            fontsize=fontsize)

def color_iterator(grouping, cmap='jet', n=None):
    '''
    Given a Matplotlib colormap, iterate through the color range in equal-sized
    increments based on the size of the group.
    
    Parameters
    ----------
    grouping : iterable
        Values to return on each iteration
    cmap : string
        Matplotlib colormap to use
    n : int
        Size of the group.  If not provided, will attempt to estimate the size
        from the iterable.
    '''

    # Attempt to get the length of the iterator first.  If we can't get the
    # length, then  we need to convert the iterator into a list so we can get
    # the number of elements.
    if n is None:
        try:
            n = len(grouping)
        except:
            grouping = list(grouping)
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
        Number of extra plots, in addition to len(groups), to reserve space for
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
    save_pattern
        TODO

    sharex and sharey are attributes that can be modified at any time during
    iteration to change the sharing behavior.

    Attributes
    ----------
    On each cycle several attributes are set that may prove useful for plotting
    (e.g. you may only want to display the Y-axis label if the axes are in the
    first column of the grid).

    first_row : bool
        True if the current axes is on the first row of the grid
    first_col : bool
        True if the current axes is on the first column of the grid
    last_row : bool
        True if the current axes is on the last row of the grid
    last_col : bool
        True if the current axes is on the last column of the grid
    '''

    def __init__(self, groups, extra=0, sharex=True, sharey=True,
                 max_groups=np.inf, adjust_spines=False, save_pattern=None,
                 auto_close=False):

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
        self.adjust_spines = adjust_spines
        self.current_figure = None
        self.figure_count = 0
        self.save_pattern = save_pattern
        self.auto_close = auto_close

        # None means they are uninitialized
        self.first_row = None
        self.first_col = None
        self.last_row = None
        self.last_col = None

    def __iter__(self):
        return self

    def next(self):
        g = self.group_iter.next()
        ax = self.next_axes()
        return  ax, g

    def next_axes(self, sharex=None, sharey=None):
        # When the call to group_iter.next() raises a StopIteration exception,
        # this exception must also bubble up and terminate this generator as
        # well.  We call group_iter.next() at the very beginning as a check to
        # make sure we have not reached the end of the sequence before adding
        # the new plot to the graph.
        if sharex is None:
            sharex = self.sharex
        if sharey is None:
            sharey = self.sharey

        #if not np.isinf(self.max_groups):
        if self.i == 0:
            if self.current_figure and self.save_pattern:
                filename = self.save_pattern.format(self.figure_count)
                self.current_figure.savefig(filename)
                if self.auto_close:
                    pylab.close(self.current_figure)
            self.current_figure = pylab.figure()
            self.figure_count += 1
            self.figures.append(self.current_figure)

        if not np.isinf(self.max_groups):
            self.i = (self.i + 1) % self.max_groups
        else:
            self.i += 1

        kw = {}
        if sharex:
            kw['sharex'] = self.current_axes
        if sharey:
            kw['sharey'] = self.current_axes
        ax = self.current_figure.add_subplot(self.n_rows, self.n_cols, self.i,
                                             **kw)
        self.current_axes = ax

        # Update the class attributes indicating the position of the subplot in
        # the grid
        self.first_col = (self.i % self.n_cols) == 1 
        self.last_col = (self.i % self.n_cols) == 0
        self.first_row = self.i <= self.n_cols
        self.last_row = self.i > (self.n_cols*(self.n_rows-1))

        # Adjust the spines if requested
        if self.adjust_spines:
            if self.first_col and self.last_row:
                adjust_spines(self.current_axes, ('bottom', 'left'), 0)
            elif self.first_col:
                adjust_spines(self.current_axes, ('left'), 0)
            elif self.last_row:
                adjust_spines(self.current_axes, ('bottom'), 0)
            else:
                adjust_spines(self.current_axes, (), 0)
        return self.current_axes

    def __del__(self):
        # Be sure to save the final figure
        if self.current_figure and self.save_pattern:
            filename = self.save_pattern.format(self.figure_count)
            self.current_figure.savefig(filename)

def figure_generator(max_groups):
    '''
    If you don't know beforehand how many plots you need to generate, but want
    to put a fixed number of plots on each figure, this will handle the logic of
    creating new figures and spacing out the axes appropriately (based on
    max_groups).
    '''
    i = 0
    rows, cols = best_rowscols(max_groups)
    while True:
        if i == 0:
            figure = pylab.figure()
        ax = figure.add_subplot(rows, cols, i+1)
        adjust_spines(ax, ('bottom', 'left'))
        yield ax
        i = (i + 1) % max_groups

class FigureGenerator(object):

    def __init__(self, max_groups, save_pattern=None, auto_close=False):
        self.max_groups = max_groups
        self.i = 0
        self.rows, self.cols = best_rowscols(max_groups)
        self.figures = []
        self.figure_count = 0
        self.current_figure = None
        self.save_pattern = save_pattern
        self.auto_close = auto_close

    def __iter__(self):
        return self

    def _save_current_figure(self):
        if self.current_figure and self.save_pattern:
            filename = self.save_pattern.format(self.figure_count)
            self.current_figure.savefig(filename)

    def next(self):
        if self.i == 0:
            self._save_current_figure()
            old_figure = self.current_figure
            self.current_figure = pylab.figure()
            self.figure_count += 1

            # If closing automatically, don't keep track of old figures
            # otherwise maintain a list of the open handles
            if self.auto_close and old_figure:
                pylab.close(old_figure)
            else:
                self.figures.append(self.current_figure)

        ax = self.current_figure.add_subplot(self.rows, self.cols, self.i+1)
        adjust_spines(ax, ('bottom', 'left'))
        self.i = (self.i + 1) % self.max_groups
        return ax

    def __del__(self):
        self._save_current_figure()
