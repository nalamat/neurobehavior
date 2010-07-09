'''
Created on May 13, 2010

@author: admin_behavior
'''
import time

from cns.widgets.views.channel_view import MultipleChannelView, FFTView
from enthought.enable.api import ComponentEditor
from enthought.pyface.timer.api import Timer
from enthought.traits.api import *
from enthought.traits.ui.api import *
from cns.channel import BufferedChannel
from cns import equipment
from cns.calibrate import fft_analyze, plot_cal

class TestController(Controller):
    
    timer = Instance(Timer)
    circuit = Any
    data = Any
    data_view = Instance(MultipleChannelView, ())
    fft_view = Instance(FFTView, ())
    ch_monitor = Range(1, 16, 1)
    pause = Bool(False)
    filter = Bool(False)
    gain = Int
    flp = Float(5e3)
    fhp = Float(250)
    
    def init(self, info):
        self.timer = Timer(100, self.tick)
        self.circuit = equipment.dsp().load('test-noise', 'RZ5')
        #self.circuit = equipment.dsp().load('test-noise-RX6', 'RX6')
        self.circuit.buf.initialize()
        
        self.data = BufferedChannel(fs=self.circuit.fs, window=1)
        self.data_view = MultipleChannelView(window=.01, 
                                             value_min=-.0003, 
                                             value_max=.0003,
                                             interactive=True)
        
        self.data_view.add(self.data, color='black')
        self.fft_view.add(self.data)
        self.circuit.start()
        
    def tick(self):
        if not self.pause:
            data = self.circuit.buf.read()
            self.data.send(data)
        
    @on_trait_change('ch_monitor, gain, filter, flp, fhp')
    def update_circuit(self, name, new):
        self.circuit.set(name, new)
        
class Test(HasTraits):
        
    traits_view = View('handler.data_view.window', 'handler.ch_monitor', 'handler.pause',
                       'handler.gain', 'handler.filter', 'handler.flp', 'handler.fhp',
                       Item('handler.data_view.component.default_origin'),
                       Item('handler.data_view.component.index_scale'),
                       Item('handler.data_view.component', editor=ComponentEditor()),
                       Item('handler.fft_view.component', editor=ComponentEditor()))
    
if __name__ == '__main__':
    Test().configure_traits(handler=TestController())
    #do_fft()