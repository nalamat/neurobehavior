from traits.api import HasTraits
from traitsui.api import VGroup
from experiments.eval import Expression

class PositiveDTParadigmMixin(HasTraits):

    kw = {'context': True, 'store': 'attribute', 'log': True}

    fc = Expression(12e3, label='Center frequency (Hz)', **kw)
    level = Expression(20, label='Level (dB SPL)', **kw)
    duration = Expression(0.512, label='Duration (s)', **kw)
    rise_fall_time = Expression(0.0025, label='Rise/fall time (s)', **kw)

    dt_group = VGroup(
            'duration',
            'rise_fall_time',
            'fc',
            'level',
            label='Signal',
            show_border=True,
            )
