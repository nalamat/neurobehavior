from ..type import Animal, Cohort
from .edit_animal import animal_edit_view, animal_view
from cns import data
import operator as op
from cns.widgets.handler import FileHandler, filehandler_menubar
from enthought.pyface.api import YES, confirm
from enthought.traits.api import HasTraits, Button, Instance, Event, \
    on_trait_change, Property, File, Bool, Str
from enthought.traits.ui.api import View, HGroup, Item, VGroup, spring, \
    InstanceEditor, TabularEditor, Group
from enthought.traits.ui.tabular_adapter import TabularAdapter
import cns
import logging
log = logging.getLogger(__name__)

class AnimalAdapter(TabularAdapter):

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
        if self.item.processed: return '#E0E0FF'
        else: return '#FFFFFF'

    def get_width(self, object, trait, column):
        return self.widths[column]

animal_table = TabularEditor(adapter=AnimalAdapter(),
                             editable=False,
                             #auto_update=True,
                             update='update',
                             selected='selected',
                             dclicked='dclicked',
                             column_clicked='column_clicked',
                             right_clicked='rclicked')

class CohortViewHandler(FileHandler):

    path            = File(cns.COHORT_PATH)
    wildcard        = Str(cns.COHORT_WILDCARD)
    modified_trait  = '_modified'
    
    def new_object(self, info):
        info.object.cohort = Cohort()
        info.object._modified = False

    def load_object(self, info, file):
        info.object.cohort = data.io.load_cohort(0, file)
        info.object._modified = False

    def save_object(self, info, file):
        data.io.save_cohort(info.object.cohort, file)
        info.object._modified = False
        
    def object_modified(self, info):
        return info.object._modified

    def object_add_changed(self, info):
        if info.initialized:
            animal = info.object._animal_factory()
            if animal.edit_traits(view=animal_edit_view, parent=info.ui.control).result:
                info.object.cohort.animals.append(animal)
                info.object.selected = animal

    def object_delete_changed(self, info):
        if info.initialized and info.object.selected is not None:
            selected = info.object.selected
            mesg = 'Are you sure you want to delete animal %s?'
            if confirm(info.ui.control, mesg % selected) == YES:
                info.object.cohort.animals.remove(selected)

class CohortView(HasTraits):

    cohort = Instance(Cohort, ())
    selected = Instance(Animal)
    dclicked = Event
    rclicked = Event
    update = Event
    column_clicked = Event
    
    _modified = Bool(False)
    
    @on_trait_change('column_clicked')
    def sort(self, event):
        return
        if event is not None:
            attr = event.editor.adapter.columns[event.column][1]
            key = op.attrgetter(attr)
            print attr, key
            #self.cohort.animals.sort(key=op.attrgetter(attr))
            #print event, event.column, event.editor, event#.item, event.row

    @on_trait_change('cohort.+, cohort.animals.+')
    def set_modified(self):
        self._modified = True
        
    @on_trait_change('cohort.animals.+')
    def sort_animals(self):
        #self.cohort.animals.sort()
        #self.update = True
        return

    view = View(VGroup(Group('object.cohort.description~',
                       ),
                       Item('object.cohort.animals', editor=animal_table,
                            show_label=False, style='readonly'),
                       Item('selected', style='custom',
                            editor=InstanceEditor(view=animal_view),
                            visible_when='selected is not None',
                            show_label=False),
                       ),
                height=0.5,
                width=0.5,
                resizable=True,
                handler=CohortViewHandler
                )

class CohortEditView(CohortView):

    add = Button('Add animal')
    delete = Button('Delete animal')

    def _animal_factory(self):
        if self.selected is not None:
            return Animal(parents=self.selected.parents,
                          birth=self.selected.birth,
                          sex=self.selected.sex)
        else: return Animal()

    def trait_view(self, parent=None):
        group = VGroup(Group('object.cohort.description'),
                       HGroup(spring, 'add', 'delete', show_labels=False),
                       Item('object.cohort.animals', editor=animal_table,
                            show_label=False, style='readonly'),
                       Item('selected', style='custom', show_label=False,
                            editor=InstanceEditor(view=animal_edit_view)))

        view = View(group,
                    title='Cohort Editor',
                    menubar=filehandler_menubar(),
                    height=0.7,
                    width=0.7,
                    resizable=True,
                    handler=CohortViewHandler(),
                    )

        return view
