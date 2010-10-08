from ..type import Animal, Cohort
from .edit_animal import animal_edit_view, animal_view
from cns.data import io
import operator as op
from cns.widgets.handler import FileHandler, filehandler_menubar
from enthought.pyface.api import YES, confirm
from enthought.traits.api import HasTraits, Button, Instance, Event, \
    on_trait_change, Property, File, Bool, Str, List
from enthought.traits.ui.api import View, HGroup, Item, VGroup, spring, \
    InstanceEditor, TabularEditor, Group
from enthought.traits.ui.tabular_adapter import TabularAdapter
import cns
import logging
log = logging.getLogger(__name__)

sex_colormap = {'M': '#ADD8E6',
                'F': '#FFB6C1',
                'U': '#D3D3D3'}

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
        if self.item.sex == 'M':
            return '#ADD8E6'
        elif self.item.sex == 'F':
            return '#FFB6C1'
        else:
            return '#D3D3D3'
    
simple_cohort_table = TabularEditor(adapter=SimpleAnimalAdapter(),
                                    editable=False,
                                    dclicked='dclicked_animal',
                                    selected='selected_animal',
                                    multi_select=False)

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
            if animal.edit_traits(view=animal_edit_view, parent=info.ui.control).result:
                info.object.cohort.animals.append(animal)
                info.object.selected = animal

    def object_delete_changed(self, info):
        if info.initialized and info.object.selected is not None:
            selected = info.object.selected
            mesg = 'Are you sure you want to delete animal %s?'
            if confirm(info.ui.control, mesg % selected) == YES:
                info.object.cohort.animals.remove(selected)

dynamic_cohort_table = TabularEditor(adapter=AnimalAdapter(), update='update',
                                     selected='selected', dclicked='dclicked',
                                     column_clicked='column_clicked',
                                     right_clicked='rclicked')

from enthought.traits.api import Any

class CohortView(HasTraits):

    cohort = Instance(Cohort, ())
    selected = Instance(Animal)
    dclicked = Event
    rclicked = Event
    update = Event
    column_clicked = Event
    
    _modified = Bool(False)

    application = Any
    
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
    def set_modified(self, object, name, old, new):
        if name != 'processed':
            self._modified = True

    @on_trait_change('dclicked')
    def open_view(self):
        print 'detected'
        view = TraitsUIView(id='foo',
                            name='foo',
                            obj=self.selected)
        self.window.add_view(view)
        
    #@on_trait_change('cohort.animals.+')
    #def sort_animals(self):
    #    #self.cohort.animals.sort()
    #    #self.update = True
    #    return

    log_view = View(VGroup(Group('object.cohort.description~',
                       ),
                       Item('object.cohort.animals',
                            editor=dynamic_cohort_table, show_label=False,
                            style='readonly'),
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
    
    traits_view = View(VGroup(Group(Item('object.cohort.description', style='readonly')),
                              Item('object.cohort.animals',
                                   editor=dynamic_cohort_table,
                                   show_label=False, style='readonly')),
                       height=400,
                       width=600,
                       resizable=True)

class CohortEditView(CohortView):

    add = Button('Add animal')
    delete = Button('Delete animal')

    def _animal_factory(self):
        if self.selected is not None:
            return Animal(nyu_id=self.selected.nyu_id+1,
                          parents=self.selected.parents,
                          birth=self.selected.birth,
                          sex=self.selected.sex)
        else: return Animal()

    def trait_view(self, parent=None):
        group = VGroup(Group('object.cohort.description'),
                       HGroup(spring, 'add', 'delete', show_labels=False),
                       Item('object.cohort.animals',
                            editor=dynamic_cohort_table, show_label=False,
                            style='readonly'),
                       Item('selected', style='custom', show_label=False,
                            editor=InstanceEditor(view=animal_edit_view)))

        view = View(group,
                    title='Cohort Editor',
                    menubar=filehandler_menubar(),
                    height=400,
                    width=600,
                    resizable=True,
                    handler=CohortViewHandler(),
                    )

        return view

class CohortView(HasTraits):

    cohort = Instance('cns.data.type.Cohort')

    dclicked = Event
    selected = Instance('cns.data.type.Animal')

    simple_view = View(Item('object.cohort.animals{}',
                            editor=simple_cohort_table),
                       height=0.5, width=0.1)

    detailed_view = View(Item('object.cohort.animals{}',
                              editor=detailed_cohort_table),
                         height=0.5, width=0.5)
