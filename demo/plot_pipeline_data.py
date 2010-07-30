import sys
sys.path.append('../lib')

from numpy.random import randn

from enthought.pyface.timer.api import Timer
from enthought.traits.api import Instance, Any
from enthought.traits.ui.api import Controller

from signal_types import Channel
from widgets import MultiChannelView
from pipeline import buffer, channel_sink, simple_moving_average, broadcast, \
        moving_average

class RandController(Controller):
    '''A simple controller to generate random data and send it to a sink.'''

    timer = Instance(Timer)
    sink  = Any

    def __init__(self, *args, **kw):
        Controller.__init__(self, *args, **kw)
        self.timer = Timer(250, self.tick)

    def tick(self):
        self.sink.send(randn(10))

if __name__ == '__main__':
    sig1 = Channel(fs=10)
    sig2 = Channel(fs=10)
    # Note that we are downsampling signal 3 by using a moving average that
    # skips every 10 samples.  This demonstrates that MultiChannelView is
    # well-suited to handle displaying signals of different sampling
    # frequencies.
    sig3 = Channel(fs=1)

    sink1 = channel_sink(sig1)
    sink2 = channel_sink(sig2)
    sink3 = channel_sink(sig3)

    buf_size = 1000

    target = broadcast([buffer(buf_size, sink1), 
                        simple_moving_average(100, buffer(buf_size, sink2)),
                        moving_average(100, None, 10, buffer(buf_size/10, sink3)),
                       ])

    view = MultiChannelView()
    view.add(sig1, color='gray')
    view.add(sig2, line_width=2.0)
    view.add(sig3, line_width=1.0, color='red')

    handler = RandController(sink=target)
    view.configure_traits(handler=handler)
