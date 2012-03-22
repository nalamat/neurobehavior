from traits.api import List, CFloat, HasTraits
from traitsui.api import VGroup, Item, Label, TabularEditor
from traitsui.tabular_adapter import TabularAdapter

from experiments.evaluate import Expression

class DTParadigmMixin(HasTraits):

    kw = {'context': True, 'log': True}

    fc = Expression(2e3, label='Center frequency (Hz)', **kw)
    level = Expression(20, label='Level (dB SPL)', help='Test', **kw)
    duration = Expression(0.512, label='Duration (s)', **kw)
    rise_fall_time = Expression(0.0025, label='Rise/fall time (s)', **kw)

    # This is a list of lists.  Each entry in the list is a two-element list,
    # [frequency, max_spl].  We default to a single entry of 2 kHz with a max
    # level of 20.0 dB SPL.  By setting the minimum length of the list to 1, we
    # prevent the user from deleting the only entry in the list.  We need to use
    # CFloat here (this means accept any value that can be cast to float) since
    # the GUI widget will a string value (e.g. '80.0' rather than the actual
    # floating point value, 80.0).  By indicating that this is a list of CFloat,
    # the string value will automatically be converted to the correct type, a
    # floating-point value.
    expected_speaker_range = List(List(CFloat), [[2e3, 20.0]], minlen=1,
                                  context=True, log=False)

    dt_group = VGroup(
            VGroup(
                'duration',
                'rise_fall_time',
                'fc',
                'level',
                label='Signal',
                show_border=True,
                ),
            VGroup(
                # Let's help the user out a little with a label to remind them
                # how to add/remove values from the editor, especially since I
                # removed all the buttons that they used to have.  This uses the
                # implicit string concatenation that the Python interpreter
                # uses.  Specifically, x = 'string a' ' ' 'string b' is
                # equivalent to x = 'string a string b'. 
                Label('Select widget then hit Insert to add item '
                      'and Delete to remove item'),
                Item('expected_speaker_range', 
                     editor=TabularEditor(
                         adapter=TabularAdapter(
                            columns=['Freq. (Hz)', 'Max level (dB SPL)'], 
                            default_value=[1000.0, -20.0]
                            )
                         ),
                     show_label=False),
                label='Expected range of tones',
                show_border=True,
                ),
            )
