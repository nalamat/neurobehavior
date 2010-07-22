'''
Created on Apr 28, 2010

@author: Brad
'''

from enthought.chaco.api import ArrayDataSource, DataRange1D, PlotAxis, \
    PlotLabel, OverlayPlotContainer, Legend, BarPlot
from enthought.enable.component import Component
from enthought.enable.component_editor import ComponentEditor
from enthought.traits.api import Str, DelegatesTo, Instance, HasTraits, Bool, \
    List, Property
from enthought.traits.ui.api import View, Item

class ComponentView(HasTraits):

    component = Instance(Component)

    index_title = DelegatesTo('index_label', 'title')
    value_title = DelegatesTo('value_label', 'title')
    title = DelegatesTo('title_label', 'text')

    index_label = Instance(PlotAxis)
    value_label = Instance(PlotAxis)
    title_label = Instance(PlotLabel)

    # Show labels on axes (set to False if you are overlaying this chart on
    # another chart that already has the labels).
    show_labels = Bool(True)
    show_aids = Bool(False)

    is_template = Bool(False)

    def _index_label_default(self):
        return PlotAxis(orientation='bottom')

    def _value_label_default(self):
        return PlotAxis(orientation='left')

    def _title_label_default(self):
        return PlotLabel(overlay_position='top')

    def _add_underlays(self, component):
        if self.show_labels:
            self.title_label.component = component
            component.underlays.append(self.title_label)
            self.value_label.component = component
            component.underlays.append(self.value_label)
            self.index_label.component = component
            component.underlays.append(self.index_label)

    traits_view = View(Item('component', editor=ComponentEditor(), show_label=False))

class BarChartComponentView(ComponentView):

    component = Instance(BarPlot)

    value_min = DelegatesTo('value_range', 'low_setting')
    value_max = DelegatesTo('value_range', 'high_setting')
    index_min = DelegatesTo('index_range', 'low_setting')
    index_max = DelegatesTo('index_range', 'high_setting')

    #index_range = Instance(DataRange1D, sync=True)
    #value_range = Instance(DataRange1D, sync=True)
    index_range = DelegatesTo('component', sync=True)
    value_range = DelegatesTo('component', sync=True)

    _index_ds = Instance(ArrayDataSource, ())
    _value_ds = Instance(ArrayDataSource, ())

    def _index_range(self):
        return DataRange1D(self._index_ds)

    def _value_range(self):
        return DataRange1D(self._value_ds)

    traits_view = View(Item('component', editor=ComponentEditor(), show_label=False))

class BarChartOverlay(ComponentView):

    component = Instance(Component)
    components = List(Instance(ComponentView))
    template = Instance(ComponentView)
    traits_to_sync = Property(depends_on='template')

    # Is this necessary? Yes, for now
    _ = DelegatesTo('template')

    def _template_changed(self, old, new):
        if old is not None:
            self.component.remove(old.component)
        self.component.add(new.component)

    def add(self, **kw):
        klass = self.template.__class__
        kw['show_labels'] = False
        for trait in self.traits_to_sync:
            kw[trait] = getattr(self.template, trait)
        component = klass(**kw)
        self.components.append(component)
        return component

    def _get_traits_to_sync(self):
        return self.template.trait_names(sync=True)

    def _component_default(self):
        return OverlayPlotContainer(bgcolor='white', fill_padding=True)

    def _components_items_changed(self, event):
        for component in event.added:
            self.component.add(component.component)
            self.template.index_range.add(component._index_ds)
            self.template.value_range.add(component._value_ds)
            for trait in self.traits_to_sync:
                self.template.sync_trait(trait, component)

        for component in event.removed:
            self.component.remove(component)
            self.template.index_range.remove(component._index_ds)
            self.template.index_range.remove(component._value_ds)

    def trait_view(self, parent=None):
        return self.template.trait_view(parent)

    def add_legend(self):
        leg_data = dict([(c.title, c.component) for c in self.components])
        legend = Legend(plots=leg_data, component=self.component,
                        border_visible=False)
        self.component.underlays.append(legend)
