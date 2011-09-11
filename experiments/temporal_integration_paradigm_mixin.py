from enthought.traits.api import HasTraits
from enthought.traits.ui.api import VGroup, Include
from evaluate import Expression

class TemporalIntegrationParadigmMixin(HasTraits):
    
    kw = {'context': True, 'store': 'attribute', 'log': True}

    rise_fall_time = Expression(0.0025, label='Rise/fall time (s)', **kw)
    fc = Expression(12e3, label='Center frequency (Hz)', **kw)
    bandwidth = Expression(4e3, label='Bandwidth (Hz)', **kw)
    level = Expression(20, label='Level (dB SPL)', **kw)
    duration = Expression(0.512, label='Duration (s)', **kw)

    temporal_integration_group = VGroup(
            'duration',
            'rise_fall_time',
            'fc',
            'bandwidth',
            'level',
            label='Signal',
            show_border=True,
            )
