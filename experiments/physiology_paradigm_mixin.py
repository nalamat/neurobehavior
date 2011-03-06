from enthought.traits.api import HasTraits, Range, Int, List, Instance, Float, \
        Tuple

from enthought.traits.ui.api import View, HGroup

class MonitorSetting(HasTraits):

    channel = Range(1, 16, 1)
    gain    = Int(50e3)

    traits_view = View(HGroup('channel', 'gain'))

monitor = Tuple(Range(1, 16, 1), Float(50000))

class PhysiologyParadigmMixin(HasTraits):

    monitor_gain    = Range(0, 100, 50, init=True, immediate=True)

    monitor_speaker = Range(1, 16, 1, init=True, immediate=True)
    monitor_1       = Range(1, 16, 1, init=True, immediate=True)
    monitor_2       = Range(1, 16, 2, init=True, immediate=True)
    monitor_3       = Range(1, 16, 3, init=True, immediate=True)

    monitor_fc_highpass = Range(0, 12.5e3, 300, init=True, immediate=True)
    monitor_fc_lowpass  = Range(0, 12.5e3, 10e3, init=True, immediate=True)
