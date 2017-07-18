from os import path
import operator as op
import tables
from cns import h5
from traits.api import HasTraits, Date, Enum, Instance, \
    Property, Int, Str, List, Bool, Any
import datetime

from traitsui.menu import MenuBar, Menu, ActionGroup, Action

from cns.widgets.file_handler import FileHandler
from pyface.api import YES, confirm
from traits.api import Button, Event, on_trait_change, File
from traitsui.api import View, HGroup, Item, VGroup, spring, \
    Group, TableEditor, ObjectColumn

from cns import get_config
import logging
log = logging.getLogger(__name__)

birth_fmt = '%Y-%m-%d'

def load_animal(node):
    '''
    Load animal metadata from a HDF5 node
    '''
    kwargs = {}
    kwargs['animal_id'] = node._f_getAttr('animal_id')
    kwargs['identifier'] = node._f_getAttr('identifier')
    kwargs['sex'] = node._f_getAttr('sex')
    date_string = node._f_getAttr('birth')
    try:
        kwargs['birth'] = datetime.datetime.strptime(date_string,
                                                     birth_fmt).date()
    except ValueError:
        log.debug('Unable to parse birthdate string %r from %r', date_string,
                node)
    kwargs['parents'] = node._f_getAttr('parents')

    # Store information on how to access the animal if we need
    kwargs['_store_node'] = node
    kwargs['_store_file'] = node._v_file
    kwargs['_store_pathname'] = node._v_pathname
    kwargs['_store_filename'] = node._v_file.filename
    return Animal(**kwargs)

def save_animal(animal, node):
    '''
    Save animal metadata to a HDF5 node
    '''
    for trait, value in animal.trait_get(store=True).items():
        if isinstance(value, datetime.date):
            # Convert datetime instances to something "human-readable" in the
            # HDF5 file.
            value = value.strftime(birth_fmt)
        elif isinstance(value, unicode):
            # HDF5 does not natively support Unicode.  Convert to strings.
            value = str(value)
        node._v_attrs[trait] = value

def load_cohort(filename):
    '''
    Load a cohort file
    '''
    with tables.openFile(filename, 'r') as fh:
        animals = [load_animal(node) for node in fh.root.Cohort_0.animals]
        description = fh.root.Cohort_0._f_getAttr('description')
        return Cohort(description=description, animals=animals)

def save_cohort(cohort, filename):
    # Check to ensure that the animals in the cohort have a unique identifier
    # and sex.  It's OK to share the same identifier as long as one is male and
    # the other female.
    markers = map(op.attrgetter('identifier', 'sex'), cohort.animals)
    if len(set(markers)) < len(markers):
        raise ValueError, 'Each animal must have a unique identifier and sex'

    # If everything's OK, then save the cohort to the file 
    with tables.openFile(filename, 'a') as fh:
        cohort_node = h5.get_or_append_node(fh.root, 'Cohort_0')
        animals_node = h5.get_or_append_node(cohort_node, 'animals')
        cohort_node._v_attrs['description'] = cohort.description
        for animal in cohort.animals:
            name = '{}_{}'.format(animal.identifier, animal.sex).upper()
            animal_node = h5.get_or_append_node(animals_node, name)
            save_animal(animal, animal_node)

class SexColumn(ObjectColumn):

    SEX_COLORMAP = {'M': '#ADD8E6',
                    'F': '#FFB6C1',
                    'U': '#D3D3D3'}

    def get_cell_color(self, object):
        return self.SEX_COLORMAP[object.sex]
    
class AnimalColumn(ObjectColumn):

    def get_cell_color(self, object):
        return '#D3D3D3' if object.processed else '#FFFFFF'

cohort_editor = TableEditor(
    sortable = True,
    selected = '_selected',
    selection_mode = 'row',
    dclick = '_dclicked',
    columns=[
        AnimalColumn(name='animal_id', label='ID'),
        AnimalColumn(name='parents'),
        AnimalColumn(name='birth'),
        AnimalColumn(name='age', editable=False),
        SexColumn(name='sex'),
        AnimalColumn(name='identifier'),
        ],
)

class CohortViewHandler(FileHandler):

    path            = File(get_config('COHORT_ROOT'))
    wildcard        = Str(get_config('COHORT_WILDCARD'))

    def new_object(self, info):
        info.object.description = ''
        info.object.animals = []
        info.object._selected = None
        info.object._modified = False

    def load_object(self, info, file):
        cohort = load_cohort(file)
        info.object.description = cohort.description
        info.object.animals = cohort.animals
        info.object._modified = False

    def save_object(self, info, file):
        save_cohort(info.object, file)
        info.object._modified = False
        
    def object__add_changed(self, info):
        if not info.initialized:
            return
        if info.object._selected is not None:
            selected = info.object._selected
            animal = Animal(animal_id=selected.animal_id+1,
                            parents=selected.parents, 
                            birth=selected.birth,
                            sex=selected.sex)
        else:
            animal = Animal()
        info.object.animals.append(animal)
        info.object._selected = animal

    def object__delete_changed(self, info):
        if not info.initialized:
            return
        if info.object._selected is not None:
            selected = info.object._selected
            mesg = 'Are you sure you want to delete animal %s?'
            if confirm(info.ui.control, mesg % selected) == YES:
                info.object.animals.remove(selected)
                info.object._selected = None

class Animal(HasTraits):

    # These should be stored in the HDF5 node
    animal_id   = Int(label='Animal ID', store=True)
    sex         = Enum('U', 'M', 'F', store=True)
    identifier  = Str(store=True)
    birth       = Date(store=True)
    parents     = Str(store=True)
     
    age         = Property(Int, depends_on='birth')
    name        = Property(Str)

    # Used in the GUI to indicate whether the animal has been run that day or
    # not
    processed   = Bool(False)

    # Reference to the animal node
    _store_node = Any
    # Reference to the HDF5 file instance
    _store_file = Any

    def _get_age(self):
        try:
            return (datetime.date.today() - self.birth).days
        except:
            return -1

    def __str__(self):
        return '{} {} (ID {})'.format(self.identifier.capitalize(), self.sex,
                self.animal_id)

    def _get_name(self):
        return '%s %s' % (self.identifier.capitalize(), self.sex)
    
class Cohort(HasTraits):

    description = Str
    animals     = List(Instance(Animal))

    _selected   = Instance(Animal)
    _dclicked   = Event
    _modified   = Bool(False)
    _add        = Button('Add animal')

    @on_trait_change('description, animals.+, animals[]')
    def set_modified(self, object, name, old, new):
        if name != 'processed':
            self._modified = True

    edit_view = View(
            VGroup(
                Group('description'),
                HGroup(spring, '_add', show_labels=False),
                Item('animals', editor=cohort_editor, show_label=False),
                ),
            title='Cohort Editor',
            menubar=MenuBar(
                Menu(
                    # The methods referenced by the actions must be defined on
                    # the controller.
                    ActionGroup(
                        Action(name='New', action='new_file',
                               accelerator='Ctrl+N'),
                        Action(name='Load...', action='load_file',
                               accelerator='Ctrl+O'),
                    ),
                    ActionGroup(
                        Action(name='Save', action='save_file',
                                enabled_when='_modified', accelerator='Ctrl+S'),
                        Action(name='Save as...', action='saveas_file',
                               enabled_when='_modified'),
                    ),
                    # The & indicates which character can be pressed (in
                    # conjunction with alt) to select the menu.
                    name='&File'
                )
            ),
            height=400,
            width=500,
            resizable=True,
            handler=CohortViewHandler(),
    )

    detailed_view = View(
            VGroup(
                Group('description'),
                Item('animals', editor=cohort_editor, show_label=False),
                style='readonly'
                ),
            title='Cohort View',
            height=400,
            width=500,
            resizable=True,
            )

if __name__ == '__main__':
    Cohort().configure_traits(view='edit_view')
