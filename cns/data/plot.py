import numpy as np
from pylab import *
from rec import cluster, unique_reduce

def rec_visualize(r, groupby, x, y, axis=None, plot_kw=None):
    if plot_kw is None:
        plot_kw = {}
    if axis is None:
        axis = gca()
    for key, data in cluster(r, groupby, x):
        label = ", ".join('{}'.format(k) for k in key)
        data_x, data_y = unique_reduce(data, x, (lambda r: np.mean(r[y]),))
        axis.semilogx(data_x, data_y, lw=2, label=label, **plot_kw)
        axis.set_xlabel(x)
        axis.set_ylabel(y)
    return axis

def rec_visualize_grand(r, x, y, axis=None, plot_kw=None):
    if plot_kw is None:
        plot_kw = {}
    if axis is None:
        axis = gca()
    reduce = [lambda r: np.mean(r[y]), lambda r: np.std(r[y])]
    data_x, data_y, data_stdev = unique_reduce(r, x, reduce)
    axis.errorbar(data_x, data_y, data_stdev, c='k', lw=2, label='Grand')
    return axis

def rec_visualize_func(r, x, func, axis=None, plot_kw=None):
    if plot_kw is None:
        plot_kw = {}
    if axis is None:
        axis = gca()
    data_x, data_y = unique_reduce(r, x, [func])
    axis.semilogx(data_x, data_y, lw=2, label='Grand', **plot_kw)
    return axis
