from enthought.traits.api import *
from enthought.chaco.api import *
from channel_data_range import ChannelDataRange
from channel_plot import ChannelPlot
from ttl_plot import TTLPlot

range = ChannelDataRange()
mapper = LinearMapper(range=range)
plot_a = TTLPlot(index_mapper=mapper)
plot_b = TTLPlot(index_mapper=mapper)
range.refresh()
range.refresh()

#plot.index_mapper.range.updated = (0, 1)

#plot.index_mapper.range.updated = (2, 4)
