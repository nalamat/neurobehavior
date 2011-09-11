from enthought.chaco.api import *
from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.enable.component_editor import ComponentEditor

class CalibrationView(HasTraits):

    signal_plot = Instance(Plot)
    fft_plot = Instance(Plot)

    traits_view = View(
            HGroup(
                Item('signal_plot', editor=ComponentEditor(), show_label=False),
                Item('fft_plot', editor=ComponentEditor(), show_label=False),
                ),
            resizable=True, width=1000, height=500, title="Calibration",) 

    def __init__(self, t, signals, frequencies, fft, *args, **kwargs):
        pd_args = dict(t=t[:1e3], frequencies=frequencies, fft=fft)
        for i, s in enumerate(signals):
            pd_args['signal%d' % i] = s[:1e3]
        plotdata = ArrayPlotData(**pd_args)

        self.signal_plot = Plot(plotdata)
        self.fft_plot = Plot(plotdata)

        for i in range(len(signals)):
            sig = 'signal%d' % i
            self.signal_plot.plot(('t', sig))

        self.fft_plot.plot(('frequencies', 'fft'), index_scale='log',
                value_scale='log')
