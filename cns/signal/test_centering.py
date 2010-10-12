from enthought.traits.api import *
from enthought.traits.ui.api import *

class SubDialog(HasTraits):

    text = Str('This is a subdialog')

    view = View('text',
                resizable=True,
                buttons=['OK', 'Cancel'],
                title='Subdialog',
                close_result=True,
                kind='modal')

class DialogHandler(Controller):

    def object_popup_changed(self, info):
        SubDialog().edit_traits(parent=self.info.ui.control)

class Dialog(HasTraits):

    popup = Button

    view = View('popup')

Dialog().configure_traits(handler=DialogHandler())
