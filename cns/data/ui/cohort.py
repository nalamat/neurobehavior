from ..type import Animal, Cohort
from cns.data import io
import operator as op
from cns.widgets.handler import FileHandler, filehandler_menubar
from enthought.pyface.api import YES, confirm
from enthought.traits.api import HasTraits, Button, Instance, Event, \
    on_trait_change, Property, File, Bool, Str, List
from enthought.traits.ui.api import View, HGroup, Item, VGroup, spring, \
    InstanceEditor, TabularEditor, Group, TableEditor, ObjectColumn
from enthought.traits.ui.tabular_adapter import TabularAdapter
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn
from enthought.traits.ui.menu import Menu, Action, ActionGroup
import cns
import logging
log = logging.getLogger(__name__)

animal_edit_view = View('nyu_id', 'parents', 'birth', 'sex', 'identifier',
                        kind='livemodal',
                        buttons=['OK', 'Cancel'])

sex_colormap = {'M': '#ADD8E6',
                'F': '#FFB6C1',
                'U': '#D3D3D3'}

class AnimalColumn(ObjectColumn):

    def get_cell_color(self, object):
        if self.name == 'sex':
            return sex_colormap[object.sex]
        elif object.processed:
            return '#D3D3D3'
        else:
            return '#FFFFFF'

animal_editor = TableEditor(
        sortable=True,
        selected='selected',
        selection_mode='row',
        dclick='dclicked',
        columns=[
            AnimalColumn(name='nyu_id', label='NYU ID'),
            AnimalColumn(name='parents'),
            AnimalColumn(name='birth'),
            AnimalColumn(name='age', editable=False),
            AnimalColumn(name='sex'),
            AnimalColumn(name='identifier'),
            ],
        menu=Menu(
            Action(name='Appetitive', action='launch_appetitive'),
            Action(name='Aversive (FM)', action='launch_aversive_fm'),
            Action(name='Aversive (generic)', action='launch_aversive_generic'),
            ),
        )

class AnimalAdapter(TabularAdapter):
    """
    Adapt a list of animals to a detailed table view.
    """

    columns = [('NYU ID', 'nyu_id'),
               ('parents', 'parents'),
               ('birth', 'birth'),
               ('age (days)', 'age'),
               ('sex', 'sex'),
               ('identifier', 'identifier'), ]

    widths = [100, 75, 150, 75, 50, 100]

    birth_text = Property

    def _get_birth_text(self):
        if self.item.birth is None: return 'Unknown'
        else: return self.item.birth.strftime('%x')

    def _get_bg_color(self):
        return sex_colormap[self.item.sex]

    def get_width(self, object, trait, column):
        return self.widths[column]

detailed_cohort_table = TabularEditor(adapter=AnimalAdapter(), 
                                      editable=False)

class SimpleAnimalAdapter(TabularAdapter):
    
    columns = [('animal', 'animal')]
    
    animal_text = Property
    
    def _get_animal_text(self):
        try:
            attributes = (self.item.identifier.capitalize(), 
                          self.item.parents,
                          self.item.birth.strftime('%x'))
            return '%s\t(Litter %s born %s)' % attributes
        except:
            return 'Unknown'
        
    def _get_bg_color(self):
        return sex_colormap[self.item.sex]
    
simple_cohort_table = TabularEditor(adapter=SimpleAnimalAdapter(),
                                    editable=False,
                                    dclicked='dclicked',
                                    selected='selected',
                                    multi_select=True,
                                    show_titles=False)

class CohortViewHandler(FileHandler):

    path            = File(cns.COHORT_PATH)
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

#dynamic_cohort_table = TabularEditor(adapter=AnimalAdapter(), update='update',
#                                     selected='selected', dclicked='dclicked',
#                                     column_clicked='column_clicked',
#                                     right_clicked='rclicked', editable=True)

class CohortView(HasTraits):

    cohort = Instance(Cohort, ())
    selected = Instance(Animal)
    dclicked = Event
    rclicked = Event
    update = Event
    column_clicked = Event
    _modified = Bool(False)

    add = Button('Add animal')
    delete = Button('Delete animal')

    def _animal_factory(self):
        if self.selected is not None:
            return Animal(nyu_id=self.selected.nyu_id+1,
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
                Item('object.cohort.animals', editor=animal_editor,
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
                Item('object.cohort.animals', editor=animal_editor,
                     show_label=False, style='readonly'),
                ),
            title='Cohort View',
            height=400,
            width=600,
            resizable=True,
            )

class CohortAnalysisView(HasTraits):

    dclicked = Event
    selected = List(Instance('cns.data.type.Animal'))
    experiments = Property(depends_on='selected')

    def _get_experiments(self):
        result = []
        for animal in self.selected:
            result.extend(animal.experiments)
        return result

    cohort = Instance('cns.data.type.Cohort')

    simple_view = View(Item('object.cohort.animals{}',
                            editor=simple_cohort_table))

    detailed_view = View(Item('object.cohort.animals{}',
                              editor=detailed_cohort_table))
