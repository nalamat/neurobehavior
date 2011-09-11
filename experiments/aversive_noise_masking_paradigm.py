from enthought.traits.api import Int, Float, Instance, List, HasTraits, \
        Float, Enum
from enthought.traits.ui.api import VGroup, Item, TableEditor, ObjectColumn, \
        View, HGroup

from abstract_aversive_paradigm import AbstractAversiveParadigm

class AversiveNoiseMaskingParadigm(AbstractAversiveParadigm):
    # NOTE: Paradigms have no access to the controller, data, or experiment
    # classes!

    # The AbstractAversiveParadigm uses a "default" parameter sequence.  We want
    # to include a shock setting, so we override that default.
    warn_sequence = List(Instance(TrialShockSetting), minlen=1,
                         editor=table_editor, store='child', init=True)
    remind        = Instance(TrialShockSetting, (), store='child', init=True)
    safe          = Instance(TrialShockSetting, (), store='child', init=True)

    # This defines the default value of warn_sequence when the instance is
    # created.  This default value can be overridden by your own sequence by
    # passing it to the constructor
    # >>> AversiveNoiseMaskingParadigm(warn_sequence=my_sequence)
    # By default, we could just leave the list empty, but this is a pain when
    # testing the program because you must remember to add a setting each time
    # you launch the program.
    def _warn_sequence_default(self):
        return [TrialShockSetting()]

    # This tells my code to save the value of that attribute in the data file.
    # Note that I have introduced a new piece of metadata called "init".  When
    # init is True, the set_<attribute name> method on the controller is called
    # when the experiment is started.
    repeats             = Int(3, store='attribute', init=True)
    masker_duration     = Float(0.2, store='attribute', init=True)
    masker_amplitude    = Float(0.5, store='atribute', init=True)
    probe_duration      = Float(0.01, store='attribute', init=True)
    trial_duration      = Float(0.5, store='attribute', init=True)

    # The traits_view defined in AbstractAversiveParadigm is the default view
    # for this class.  Since the only difference between this paradigm and other
    # paradigms (e.g. frequency modulation or AM noise) are the signal
    # parameters, each paradigm creates a signal_group containing the elements
    # that should be included in the view.  In AbstractAversiveParadigm,
    # traits_view has an Include('signal_group') directive that looks for this
    # attribute and includes the contents in the view.
    signal_group = VGroup(
            Item('repeats'),
            Item('masker_duration',label='Masker duration (s)'),
            Item('masker_amplitude',label='Masker amplitude (dB SPL)'),
            Item('probe_duration',label='Probe duration (s)'),
            label='Masker Settings',
            show_border=True,
            )
    timing_group = VGroup(
            Item('min_safe',label='Minimum # safe trials'),
            Item('max_safe',label='Maximum # safe trials'),
            Item('trial_duration',label='Trial duration (s)'),
            Item('prevent_disarm',label='Prevent disarming of shock/puff?'),
            Item('aversive_delay',label='Shock/puff delay (s)'),
            Item('aversive_duration',label='Shock/puff duration (s)'),
            Item('lick_th',label='Contact threshold'),
            show_border=True,
            label='Trial settings',
            )
