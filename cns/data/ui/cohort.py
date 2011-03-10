from ..type import Animal, Cohort
from cns.data import io
from cns.widgets.handler import FileHandler, filehandler_menubar
from enthought.pyface.api import YES, confirm
from enthought.traits.api import HasTraits, Button, Instance, Event, \
    on_trait_change, Property, File, Bool, Str, List
from enthought.traits.ui.api import View, HGroup, Item, VGroup, spring, \
    InstanceEditor, Group, TableEditor, ObjectColumn
from enthought.traits.ui.tabular_adapter import TabularAdapter

import cns
import logging
log = logging.getLogger(__name__)

class AnimalColumn(ObjectColumn):

    SEX_COLORMAP = {'M': '#ADD8E6',
                    'F': '#FFB6C1',
                    'U': '#D3D3D3'}

    def get_cell_color(self, object):
        if self.name == 'sex':
            return self.SEX_COLORMAP[object.sex]
        elif object.processed:
            return '#D3D3D3'
        else:
            return '#FFFFFF'

class CohortEditor(TableEditor):

    sortable        = True
    selected        = 'selected'
    selection_mode  = 'row'
    dclick          = 'dclicked'

    columns=[
        AnimalColumn(name='nyu_id', label='ID'),
        AnimalColumn(name='parents'),
        AnimalColumn(name='birth'),
        AnimalColumn(name='age', editable=False),
        AnimalColumn(name='sex'),
        AnimalColumn(name='identifier'),
        ]

class CohortViewHandler(FileHandler):

    path            = File(cns.COHORT_ROOT)
    wildcard        = Str(cns.COHORT_WILDCARD)
    modified_trait  = '_modified'

    def new_object(self, info):
        info.object.cohort = Cohort()
        info.object._modified = False

    def load_object(self, info, file):
        info.object.cohort = io.load_cohort(0, file)
        info.object._modified = False

    def save_object(self, info, file):
        io.save_cohort(info.object.cohort, file)
        info.object._modified = False
        
    def object_modified(self, info):
        return info.object._modified

    def object_add_changed(self, info):
        if info.initialized:
            animal = info.object._animal_factory()
            info.object.cohort.animals.append(animal)
            info.object.selected = animal
            print info.object.selected

    def object_delete_changed(self, info):
        if info.initialized and info.object.selected is not None:
            selected = info.object.selected
            mesg = 'Are you sure you want to delete animal %s?'
            if confirm(info.ui.control, mesg % selected) == YES:
                info.object.cohort.animals.remove(selected)
                info.object.selected = None

class CohortView(HasTraits):

    cohort      = Instance(Cohort, ())
    selected    = Instance(Animal)
    dclicked    = Event
    rclicked    = Event
    update      = Event
    _modified   = Bool(False)

    add = Button('Add animal')
    delete = Button('Delete animal')

    def _animal_factory(self):
        if self.selected is not None:
            return Animal(animal_id=self.selected.animal_id+1,
                          parents=self.selected.parents,
                          birth=self.selected.birth,
                          sex=self.selected.sex)
        else: return Animal()

    @on_trait_change('cohort.+, cohort.animals.+')
    def set_modified(self, object, name, old, new):
        if name != 'processed':
            self._modified = True

    edit_view = View(
            VGroup(
                Group('object.cohort.description'),
                HGroup(spring, 'add', 'delete', show_labels=False),
                Item('object.cohort.animals', editor=CohortEditor(),
                     show_label=False),
                ),
            title='Cohort Editor',
            menubar=filehandler_menubar(),
            height=400,
            width=600,
            resizable=True,
            handler=CohortViewHandler(),
            )

    detailed_view = View(
            VGroup(
                Group(Item('object.cohort.description', style='readonly')),
                Item('object.cohort.animals', editor=CohortEditor(),
                     show_label=False, style='readonly'),
                ),
            title='Cohort View',
            height=400,
            width=600,
            resizable=True,
            )
