'''
Created on May 26, 2010

@author: Brad
'''
from enthought.traits.api import HasTraits, Instance
from enthought.traits.ui.api import Handler, UIInfo

class ToolBar(HasTraits):

    handler = Instance(Handler)
    info = Instance(UIInfo)

    def install(self, handler, info):
        self.handler = handler
        self.info = info

    def _anytrait_changed(self, trait, value):
        # Discard any trait changes that are not due to the buttons defined in
        # the subclasses.
        if trait not in ('trait_added', 'info', 'handler'):
            getattr(self.handler, trait)(self.info)
