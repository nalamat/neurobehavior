from enthought.pyface.api import confirm, YES
from enthought.traits.api import HasTraits, on_trait_change, Any, Date, Time, \
    Property, Str, Button
from enthought.traits.ui.api import View, VGroup, Item, Handler, HGroup, spring, \
    TabularEditor
from enthought.traits.ui.tabular_adapter import TabularAdapter
from cns.widgets import H_BUTTON, W_BUTTON
from cns.widgets import icons
import datetime
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.etsconfig.api import ETSConfig

class DateAdapter(TabularAdapter):
    
    col_label       = Str
    date_text       = Property
    #date_bg_color   = Property

    widths = [150, 50]

    def get_width(self, object, trait, column):
        return self.widths[column]
    
    @on_trait_change('col_label')
    def set_columns(self):
        self.columns= [('date', 'date'), (self.col_label, 1)]

    def _get_date_text(self):
        return self.item[0].strftime('%x %H:%M')

    def _get_bg_color(self):
        if self.item[1] == 'ON WATER': return '#E0E0FF'
        else: return '#FFFFFF'

class DateTableEditHandler(Handler):

    def object_delete_changed(self, info):
        if info.object.selected is not None:
            selected = info.object.selected
            mesg = 'Are you sure you want to delete record %s %s?'
            if confirm(info.ui.control, mesg % selected) == YES:
                info.object.table.remove(selected)
                info.object.selected = None
                info.object.update = True

    def object_add_changed(self, info):
        dlg = AddDatedRecordDialog(new_value_type=info.object.new_value_type)

        if dlg.edit_traits(parent=info.ui.control).result:
            date = datetime.datetime.combine(dlg.new_date, dlg.new_time)
            info.object.table.append((date, dlg.new_value))
            info.object.table.sort()
            info.object.update = True

class DateTableEditor(HasTraits):

    table           = Any
    new_value_type  = Any
    col_label       = Str
    update          = Button
    selected        = Any
    
    if ETSConfig.toolkit == 'wx':
        add             = Button('+')
        delete          = Button('-')

    else:
        item_kw         = dict(height=16, width=16)
    
        add             = SVGButton(tooltip='add record', 
                                    filename=icons.add,
                                    **item_kw)
        delete          = SVGButton(tooltip='delete record', 
                                    filename=icons.delete,
                                    **item_kw)
    
    def traits_view(self):
        editor = TabularEditor(adapter=DateAdapter(col_label=self.col_label),
                               update='update',
                               editable=False,
                               selected='selected')
                                
        return View(HGroup(spring, 
                           Item('add'),
                           Item('delete'),
                           show_labels=False),
                    Item('table', show_label=False, editor=editor),
                    resizable=True,
                    handler=DateTableEditHandler,
                    )

class AddDatedRecordDialog(HasTraits):

    new_value_type = Any
    new_date = Date
    new_time = Time
    new_value = Any

    datetime = Any

    @on_trait_change('new_value_type')
    def update_type(self, type):
        self.add_trait('new_value', type)

    def _new_date_default(self):
        return datetime.date.today()

    def _new_time_default(self):
        return datetime.datetime.now().time()

    def traits_view(self):
        return View('new_value', 
                    VGroup(Item('new_date', label='Date'),
                           Item('new_time', label='Time'),
                           label='Add at',
                           show_border=True),
                    kind='livemodal',
                    x=0.5,
                    y=0.5,
                    resizable=True,
                    buttons=['OK', 'Cancel'])
