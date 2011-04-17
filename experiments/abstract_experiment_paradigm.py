from enthought.traits.api import HasTraits, Enum, Property

class AbstractExperimentParadigm(HasTraits):

    speaker_mode = Enum('primary', 'secondary', 'both', 'random',
                        store='attribute', label='Speaker mode', init=True)

    parameter_names = Property
    parameter_info = Property

    def _get_parameter_names(self):
        return self.editable_traits()

    def _get_parameter_info(self):
        return dict((n, self.trait(n).label) for n in self.editable_traits())

    def is_valid(self):
        for trait in self.trait_names(error=True):
            # Return False if any of the error traits are True
            if getattr(self, trait):
                return False
        return True
    
    def err_messages(self):
        messages = []
        for trait in self.class_trait_names():
            if trait.startswith('err') and getattr(self, trait):
                mesg_prop = 'mesg_%s' % trait[4:]
                messages.append(getattr(self, mesg_prop))
        return '\n'.join(messages) if messages else 'No errors found'
