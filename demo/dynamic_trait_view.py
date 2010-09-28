from enthought.traits.api import HasTraits, Button, Int, Instance, Property
from enthought.traits.ui.api import Item, View, InstanceEditor, Handler

class Camera(HasTraits):
    genView = Property
    
    def _get_genView(self):
        trait_names = self.editable_traits()
        trait_names.remove('genView')
        return View(trait_names)
            
class CameraWrapper(HasTraits):
    camera = Instance(Camera)
    generate_button = Button()

    trait_view = View(Item('generate_button'),
                  Item('camera', editor=InstanceEditor(view_name='object.camera.genView'), 
                       style='custom'),
                       resizable=True)
    
    def _generate_button_fired(self):
        camera = self.camera
        tname = 't' + str((len(camera.trait_names())-2))
        camera.add_trait(tname, Int())
        setattr(camera, tname, 0)
        camera.trait_property_changed('genView', None, camera.genView)
    
if __name__ == "__main__":
    camera = Camera()
    camera_wrapper = CameraWrapper(camera=camera)
    camera_wrapper.configure_traits()
