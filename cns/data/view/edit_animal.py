from ..constants import ANIMAL_STATUS
from ..type import Animal
from .edit_date_record import DateTableEditor
from enthought.traits.api import on_trait_change, Button, Str, Instance, \
    Property, CFloat, Enum
from enthought.traits.ui.api import Handler, View, Item, HGroup, Group, \
    Controller

class AnimalEditHandler(Controller):

    animal = Instance(Animal)
    weight_log_editor = Instance(DateTableEditor)
    status_log_editor = Instance(DateTableEditor)

    @on_trait_change('animal')
    def update_weight_log(self):
        editor = DateTableEditor(table=self.animal.weight_log,
                                 new_value_type=CFloat,
                                 col_label='weight')
        self.weight_log_editor = editor

    @on_trait_change('animal')
    def _status_log_editor_default(self):
        editor = DateTableEditor(table=self.animal.status_log,
                                 new_value_type=Enum(*ANIMAL_STATUS),
                                 col_label='status')
        self.status_log_editor = editor

    def init(self, info):
        try: self.animal = info.object.animal
        except: self.animal = info.object

animal_edit_view = View([  ['nyu_id{NYU ID}', 'parents', 'birth', 'sex', 'identifier'],
                           'handler.weight_log_editor{}@<>',
                           'handler.status_log_editor{}@<>',
                           '-', ],
                        handler=AnimalEditHandler(),
                        buttons=['OK', 'Cancel'],
                        resizable=True,
                        kind='livemodal',
                        width=0.4,
                        )

animal_view = View(HGroup(Group(Item('handler.weight_log_editor',
                                     style='custom',
                                     show_label=False,),
                                springy=True,
                                ),
                          Group(Item('handler.status_log_editor',
                                     show_label=False,
                                     style='custom'),
                                springy=True,
                                ),
                          ),
                   handler=AnimalEditHandler(),
                   resizable=True,
                   kind='panel',
                   )