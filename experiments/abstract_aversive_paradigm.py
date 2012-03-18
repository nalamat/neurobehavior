from enthought.traits.api import Bool
from enthought.traits.ui.api import VGroup

from abstract_experiment_paradigm import AbstractExperimentParadigm

from evaluate import Expression

class AbstractAversiveParadigm(AbstractExperimentParadigm):
    '''
    Defines an aversive paradigm, but not the signals that will be used.  This
    allows us to use either a generic circuit with two buffers for the warn/safe
    signal, or a circuit that is specialized for a specific kind of signal (e.g.
    FM).
    '''

    kw = {'context': True, 'log': True}

    prevent_disarm = Bool(True, label='Prevent disarm of aversive?', **kw)

    # By default, Range provides a slider as the GUI widget.  Note that you can
    # override the default widget if desired.
    lick_th = Expression(0.75, label='Contact threshold', **kw)
    aversive_delay = Expression(1, label='Aversive delay (s)', **kw)
    aversive_duration = Expression(0.3, label='Aversive duration (s)', **kw)
    trial_duration = Expression(1.0, label='Trial duration (s)', **kw) 
    shock_level = Expression(0.0, label='Shock level (mA)', **kw)

    abstract_aversive_paradigm_group = VGroup(
            'prevent_disarm',
            'trial_duration',
            'aversive_delay',
            'aversive_duration',
            'shock_level',
            'lick_th',
            show_border=True,
            label='Paradigm',
            )
