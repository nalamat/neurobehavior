from enthought.traits.api import HasTraits

class AbstractExperimentParadigm(HasTraits):

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
