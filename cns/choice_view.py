import inspect
from enthought.traits.api import HasTraits, Str, Property, List, Trait, \
        Instance, on_trait_change, Button, Bool, Enum, CInt
from enthought.traits.ui.api import View, Item, HGroup, ListStrEditor, VGroup, \
        Label
import choice
import util

def isselector(x):
    return type(x)==type(object) and \
           issubclass(x, choice.Choice) and \
           x is not choice.Choice
       
parse_name = lambda x: util.convert(x, ' ').replace('choice', '').strip()
klasses = inspect.getmembers(choice, isselector)
options = [(parse_name(klass[0]), klass[1]) for klass in klasses]
options = dict(options)

class ChoiceView(HasTraits):

    sequence  = List(Str)
    order     = Trait('descending', options)
    mode      = Enum('in-place', 'delayed', 'restart')
    selector  = Instance(choice.Choice)
    next      = Button

    @on_trait_change('order')
    def _update_selector(self):
        self.selector = self.order_(self.sequence)

    def _selector_default(self):
        sequence = [float(s) for s in self.sequence if s]
        return self.order_(sequence)

    @on_trait_change('sequence[]')
    def dispatch_sequence_change(self, object, names, removed, added):
        # For some reason two triat_change notifications are made each time an
        # item is added or removed.  The second notification contains null
        # strings for removed and added, so we can recognize the second
        # notification.  This may be because of the auto add option which adds a
        # hidden "" to the end of the list).  I haven't really bothered to debug
        # this, so we will just discard the trait_change notifications that are
        # empty.
        if removed or added:
            print self.sequence
            sequence = [float(s) for s in self.sequence if s]
            if self.mode == 'restart':  
                self.selector = self.order_(sequence)
            if self.mode == 'in-place':
                par = self.selector.next()
                print par
                self.selector = self.order_(sequence, par)
            if self.mode == 'delayed':
                self.selector = self.order_(sequence, self.selector.sequence)

    def _parse_string(self, sequence):
        '''Not used currently'''
        separators = ';,.'
        if type(sequence) == type(''):
            for s in ';,.':
                sequence.replace(s, ' ')
            return np.asarray(sequence.strip().split()).astype('f')
        else:
            return sequence

    def _next_fired(self):
        print self.selector.next()

    sequence_editor = ListStrEditor(auto_add=True, multi_select=True)
    traits_ui_view = View(
            VGroup(Item('order', show_label=False),
                   Item('mode', show_label=False, style='custom'),
                   Item('sequence', editor=sequence_editor, show_label=False),
                   Item('next'),
                   ),
            resizable=True)

ChoiceView().configure_traits()

def test_in_place_descending_choice():
    seq = 1, 2, 3, 4
    choice = InPlaceDescendingChoice(seq)

    selections = [choice() for i in range(10)]
    expected = [4, 3, 2, 1, 4, 3, 2, 1, 4, 3]

    choice.sequence = 0.5, 1, 2, 3, 4
    selections.extend([choice() for i in range(5)])
    expected.extend([2, 1, 0.5, 4, 3])

    choice.sequence = 0.25, 0.5, 1, 2, 3, 4, 5
    selections.extend([choice() for i in range(5)])
    expected.extend([2, 1, 0.5, 0.25, 5])

    choice.sequence = 8, 9, 10
    selections.extend([choice() for i in range(5)])
    expected.extend([10, 9, 8, 10, 9])
    
    print selections
    print expected

def test_delayed_descending_choice():

    sequence = 1, 2, 3, 4
    choice = DelayedDescendingChoice(sequence)

    selections = [choice() for i in range(10)]
    expected = [4, 3, 2, 1, 4, 3, 2, 1, 4, 3]

    choice.sequence = -1, -2, -3, -4
    selections.extend([choice() for i in range(10)])

    expected.extend([2, 1, -1, -2, -3, -4, -1, -2, -3, -4])

    print selections
    print expected

