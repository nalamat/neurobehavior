from enthought.traits.api import Int, Float, Instance, List, HasTraits, \
        Float, Enum
from enthought.traits.ui.api import VGroup, Item, TableEditor, ObjectColumn, \
        View, HGroup

from abstract_aversive_paradigm import AbstractAversiveParadigm

class TrialShockSetting(HasTraits):

    parameter           = Float(store='attribute')
    shock_level         = Float(store='attribute')
    traits_view         = View('parameter', 'shock_level')

    def __str__(self):
        # When you call str(object), it returns a string that can be displayed
        # in the GUI or command line.  The default string representation of an
        # object is quite ugly (and uninformative).  We override the __str__
        # special method to provide a more refined string describing what this
        # setting is.
        return "{0} dB SPL @ {1}".format(self.parameter, self.shock_level)

    def __cmp__(self, other):
        # Lists of Python objects are sorted using the special __cmp__ method.
        # If you do not provide an implementation of the __cmp__ method, then
        # sorting your list of settings likely will not work the way you expect!
        # I believe the default sort order is based on the hash of the object.
        # Since sorting is used by some of the selectors in cns.choice (e.g. for
        # ascending or descending sequences), we need to ensure that a list of
        # instances is sorted the way we want (by parameter).  Luckily, Python
        # provides a built-in cmp function that can do most of the work for us.
        # All we have to do is pass the parameter from this object and the
        # object we are comparing to cmp and return the result.
        return cmp(self.parameter, other.parameter)

# A "factory" is a callable that returns a new instance.  A callable is
# essentially something that can be followed by parenthesis, ().  Functions are
# callables, classses are callables, etc.  When we call the class object,
# TrialShockSetting (e.g. setting = TrialShockSetting()), we get an instance
# back.  Hence, TrialShockSetting is a factory.
table_editor = TableEditor(
        reorderable=True,       # Can we reorder via the GUI?
        editable=True,          # Can we edit the contents via the GUI?
        deletable=True,         # Can we delete items?
        show_toolbar=True,      
        row_factory=TrialShockSetting,
        selection_mode='cell',
        columns=[
            ObjectColumn(name='parameter', label='Tone level (dB SPL)',
                         width=75),
            ObjectColumn(name='shock_level', label='Shock level', width=75),
            ]
        )

class AversiveNoiseMaskingParadigm(AbstractAversiveParadigm):
    # NOTE: Paradigms have no access to the controller, data, or experiment
    # classes!

    # You may override defaults defined in a superclass simply by assigning the
    # value here.
    min_safe        = 1
    max_safe        = 4
    trial_duration  = 0.5

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
            Item('masker_duration'),
            Item('masker_amplitude'),
            Item('probe_duration'),
            label='Masker Settings',
            show_border=True,
            )
    timing_group = VGroup(
            Item('prevent_disarm'),
            Item('aversive_duration'),
            Item('lick_th'),
            show_border=True,
            label='Trial settings',
            )
            
