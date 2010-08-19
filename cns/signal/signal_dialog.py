from cns.signal import Signal, type as st
from cns.signal.type import signal_types
from cns.signal.view_factory import signal_view_factory
from enthought.traits.api import HasTraits, Instance, Str, Bool
from enthought.traits.ui.api import View, Item, InstanceEditor
from enthought.traits.ui.instance_choice import InstanceFactoryChoice

class StrictChoice(InstanceFactoryChoice):

    allow_par = Bool(True)

    def is_compatible(self, object):
        '''The default behavior is to return true if object is a subclass of
        self.klass.  Since we use subclassing to generate various signal types
        (e.g. AMTone is a subclass of Tone), we require that the class of the
        object be the class represented by this choice.
        '''
        return object.__class__ is self.klass

    def get_view(self):
        return signal_view_factory(self.klass, include_variable=self.allow_par)

class SignalDialog(HasTraits):
    '''Generates a signal selector dialog.  This is basically a loose wrapper
    around the InstanceEditor class.
    '''
    signal = Instance(Signal)
    title = Str('Edit Signal')
    allow_par = Bool(True)

    def traits_view(self, parent=None):
        choices = [StrictChoice(name=n, klass=s, allow_par=self.allow_par) \
                   for s, n in signal_types.items()]
        return View(Item('signal{}@', editor=InstanceEditor(values=choices)),
                    height=400,
                    resizable=True,
                    title=self.title,
                    kind='modal',
                    close_result=False,
                    buttons=['OK', 'Cancel'])

if __name__ == '__main__':
    sd = SignalDialog(signal=st.AMTone(), allow_par=False)
    #sd.configure_traits(view='dialog_selector_view')
    sd.configure_traits()
