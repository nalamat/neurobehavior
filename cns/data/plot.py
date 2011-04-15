from matplotlib import ticker
from pylab import *
from rec import cluster

def rec_visualize(r, groupby, x, y, axis=None):
    if axis is None:
        axis = gca()
    for key, data in cluster(r, groupby):
        indices = data[x].argsort()
        label = ", ".join('{}'.format(k) for k in key)
        axis.semilogx(data[x][indices], data[y][indices], lw=2, label=label)
        axis.set_xlabel(x)
        axis.set_ylabel(y)
        #loc = ticker.LogLocator(base=2)
        #fmt = ticker.LogFormatterMathtext(base=2, labelOnlyBase=False)
        #axis.xaxis.set_major_formatter(fmt)
        #axis.xaxis.set_major_locator(loc)
