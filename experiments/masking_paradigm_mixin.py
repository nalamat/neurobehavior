from enthought.traits.api import HasTraits
from enthought.traits.ui.api import VGroup, Item
from evaluate import Expression

class MaskingParadigmMixin(HasTraits):

    '''
    context
        When true, all changes to the value of the parameter in the GUI will be
        captured by the apply/revert controller, requiring the user to manually
        hit apply to commit the change (or revert it back to its original
        value).  In addition, the parameter is included in the "namespace" that
        is used to evaluate the various parameter expressions that are
        recomputed on each trial.
    immediate
        When true (context must also be true), the change is applied
        immediately, bypassing the apply/revert controller.  This is used to
        allow users to immediately change the shock setting.
    store
        How should the value of the parameter be stored in the HDF5 file
        (setting to 'attribute' is sufficient for the majority of parameters you
        will have).
    log
        If true, save the current value of the parameter in the trial log
    '''

    # Because the majority of parameters should be tracked by the apply/revert
    # controller and logged to the trial log file, I set up a variable
    # containing the appropriate keywords.
    kw = {'context': True, 'store': 'attribute', 'log': True }

    #repeats             = Expression(2, label='Repeats', **kw)

    masker_duration     = Expression(0.5, label='Masker duration (s)', **kw)
    masker_delay        = Expression(0, label='Masker delay re trial start (s)', **kw)
    masker_bandwidth    = Expression('probe_freq*0.3', label='Masker bandwidth (Hz)', **kw)
    masker_level        = Expression(90.0, label='Masker spectrum level (dB SPL)', **kw)
    probe_freq          = Expression(4000, label='Probe frequency (Hz)', **kw)
    probe_duration      = Expression(0.02, label='Probe duration (s)', **kw)
    probe_delay         = Expression(0, label='Probe delay re trial start (s)', **kw)
    probe_level         = Expression(80.0, label='Probe level (dB SPL)', **kw)

    # The traits_view defined in AbstractAversiveParadigm is the default view
    # for this class.  Since the only difference between this paradigm and other
    # paradigms (e.g. frequency modulation or AM noise) are the signal
    # parameters, each paradigm creates a signal_group containing the elements
    # that should be included in the view.  In AbstractAversiveParadigm,
    # traits_view has an Include('signal_group') directive that looks for this
    # attribute and includes the contents in the view.
    signal_group = VGroup(
            #Item('repeats'),
            Item('masker_delay'),
            Item('masker_duration'),
            Item('masker_level'),
            Item('masker_bandwidth'),
            Item('probe_freq'),
            Item('probe_duration'),
            Item('probe_delay'),
            Item('probe_level'),
            label='Masker Settings',
            show_border=True,
            )
