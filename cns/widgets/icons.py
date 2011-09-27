import os

FILE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
STYLE = 'oxygen'
SIZE = 'scalable'

RESOURCE_PATH = os.path.join(FILE_DIRECTORY, 'resource/', STYLE, SIZE)
#RESOURCE_PATH = r'C:\experiments\programs\stable\neurobehavior\cns\widgets\resource\oxygen\scalable'

oxygen_icons = {'start':        'actions/1rightarrow.svgz',
                'warn':         'actions/messagebox_warning.svg',
                'stop':         'actions/stop.svgz',
                'apply':        'actions/system_run.svgz',
                'apply_now':    'actions/system_restart.svgz',
                'pause':        'actions/player_pause.svgz',
                'resume':       'actions/player_play.svgz',
                'configure':    'actions/configure_toolbars.svg',
                'add':          'actions/plus.svg',
                'delete':       'actions/remove.svgz',
                'undo':         'actions/undo.svgz',
                'up':           'actions/go-up.svgz',
                'down':         'actions/go-down.svgz',
                'right2':       'actions/2rightarrow.svgz',
                'left2':        'actions/2leftarrow.svgz',
                }

for k, v in globals()[STYLE+'_icons'].items():
    globals()[k] = os.path.join(RESOURCE_PATH, v)
                
def button_test():
    from enthought.traits.api import HasTraits
    from enthought.traits.ui.api import View, Item
    from enthought.savage.traits.ui.svg_button import SVGButton
    
    class TestButtons(HasTraits):    
        pass
    
    test_buttons = TestButtons()    
    items = []
    for button in oxygen_icons:
        filename = globals()[button]        
        trait = SVGButton(button, filename=filename)
        print button, filename
        test_buttons.add_class_trait(button, trait)
        items.append(Item(button))
        
    test_buttons.configure_traits(view=View(*items))
    
if __name__ == '__main__':
    button_test()
        