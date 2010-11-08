from enthought.traits.api import HasTraits, Property, Bool, Str
import numpy as np

import logging
log = logging.getLogger(__name__)

class Paradigm(HasTraits):

    def is_valid(self):
        for trait in self.class_trait_names():
            if trait.startswith('err') and getattr(self, trait):
                return False
        return True
    
    def err_messages(self):
        messages = []
        for trait in self.class_trait_names():
            if trait.startswith('err') and getattr(self, trait):
                mesg_prop = 'mesg_%s' % trait[4:]
                messages.append(getattr(self, mesg_prop))
        if messages: return '\n'.join(messages)
        else: return 'No errors found'
