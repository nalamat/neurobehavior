from cns.widgets.views.component_view import BarChartComponentView, BarChartOverlay
from enthought.chaco.api import BarPlot, DataRange1D, LinearMapper, LabelAxis, ArrayDataSource
from enthought.traits.ui.api import View, Item, Group
from enthought.enable.component_editor import ComponentEditor
from enthought.traits.api import Str, Int, Float, Trait, Any, Callable, \
    Instance, HasTraits, DelegatesTo, on_trait_change
import numpy as np

#class SingleBarPlot(BarPlot):
#
#    source = Instance(HasTraits, ())
#    index_trait = Str
#    value_trait = Str
#
#    index = Instance(ArrayDataSource, ())
#    value = Instance(ArrayDataSource, ())
#
#    index_spacing = Int(1)
#
#    def _get_values(self):
#        if self.source is not None:
#            value = np.array(getattr(self.source, self.value))
#            if self.preprocess_values is not None:
#                value = self.preprocess_values(value)
#            return value
#        else:
#            return []
#
#    def _get_indices(self):
#        values = self._get_values()
#        return range(0, len(values) * self.index_spacing, self.index_spacing)
#
#    def _source_changed(self, old, new):
#        if old is not None:
#            old.on_trait_change(self._data_changed, self.index_trait,
#                                remove=True)
#            old.on_trait_change(self._data_changed, self.value_trait,
#                                remove=True)
#        if new is not None:
#            new.on_trait_change(self._data_changed, self.index_trait)
#            new.on_trait_change(self._data_changed, self.value_trait)
#
#    def _data_changed(self):
#        index = self._get_index()
#        value = self._get_value()
#        if len(index) == len(value):
#            self.index.set_data(index)
#            self.value.set_data(value)

class SingleBarPlotView(BarChartComponentView):

    # Formatting of index axis
    label_fmt = Str('%r')
    index_spacing = Int(1)

    # Information about data to plot
    value = Str

    source = Any
    bar_width = DelegatesTo('component')
    bar_color = DelegatesTo('component', 'fill_color')

    preprocess_values = Trait(None, Callable, sync=True)

    def __init__(self, *args, **kw):
        super(SingleBarPlotView, self).__init__(*args, **kw)
        self.update_data()

    def _get_indices(self):
        raise NotImplementedError

    def _get_values(self):
        if self.source is not None:
            value = np.array(getattr(self.source, self.value))
            if self.preprocess_values is not None:
                value = self.preprocess_values(value)
            return value
        else:
            return []

    def _component_default(self):
        component = BarPlot(
                index=self._index_ds,
                value=self._value_ds,
                index_mapper=LinearMapper(range=self._index_range()),
                value_mapper=LinearMapper(range=self._value_range()),
                line_color='transparent',
                padding=50,
                bgcolor='white',
                fill_padding=True,
                border_visible=False,
                )
        self._add_underlays(component)
        return component

    def _index_label_default(self):
        label_position, label_text = self._get_labels()
        return LabelAxis(labels=label_text,
                         positions=label_position,
                         orientation='bottom')

    def _index_range(self):
        return DataRange1D(self._index_ds, bounds_func=self.bounds_func)

    def bounds_func(self, data_low, data_high, margin, tight_bounds):
        return data_low - 0.5, data_high + 0.5

    def update_data(self):
        if self.traits_inited() and not self.is_template:
            index = self._get_indices()
            value = self._get_values()
            if len(index) == len(value):
                self._index_ds.set_data(index)
                self._value_ds.set_data(value)

class DynamicBarPlotView(SingleBarPlotView):

    label = Trait(None, Str)

    def __init__(self, *args, **kw):
        super(DynamicBarPlotView, self).__init__(*args, **kw)
        self.update_labels()

    def _get_indices(self):
        values = self._get_values()
        return range(0, len(values) * self.index_spacing, self.index_spacing)

    def _get_labels(self):
        indices = self._get_indices()
        if self.label is None:
            labels = indices
        else:
            labels = np.array(getattr(self.source, self.label))
        #label_text = [(self.label_fmt % l) for l in labels]
        label_text = [('%.4f' % l).rstrip('0') for l in labels]
        return indices, label_text

    @on_trait_change('source', 'label')
    def update_listeners(self, old, new):
        if old is not None:
            old.on_trait_change(self.update_labels, self.label, remove=True)
            old.on_trait_change(self.update_data, "updated", remove=True)
        if new is not None:
            new.on_trait_change(self.update_labels, self.label)
            new.on_trait_change(self.update_data, "updated")

    @on_trait_change('label', 'source')
    def update_labels(self):
        if self.traits_inited():
            label_position, label_text = self._get_labels()
            self.index_label.positions = label_position
            self.index_label.labels = label_text

class HistoryBarPlotView(SingleBarPlotView):

    history = Int(10, sync=True)
    label_fmt = '%d'
    index = Trait(None, Str)
    current_index = Trait(None, None, Int, sync=True)

    def _get_indices(self):
        if self.index is None:
            values = self._get_values()
            return range(-len(values) * self.index_spacing, 0, self.index_spacing)
        else:
            index = np.asarray(getattr(self.source, self.index))
            if self.current_index is not None:
                index -= self.current_index
            else:
                try: index -= index.max()
                except ValueError: pass
            return index

    def _get_labels(self):
        labels = np.arange(-self.history, 0)
        return labels, [(self.label_fmt % l) for l in labels]

    def bounds_func(self, data_low, data_high, margin, tight_bounds):
        return - self.history - 0.5, 0.5

    def _source_changed(self, old, new):
        items = [self.value, self.value + '_items']
        if self.index is not None:
            items.append(self.index)
            items.append(self.index + '_items')
        for item in items:
            if old is not None:
                old.on_trait_change(self.update_data, item, remove=True)
            new.on_trait_change(self.update_data, item)

    def _current_index_changed(self):
        self.update_data()
        self.index_range.refresh()

    def _history_changed(self):
        if self.traits_inited():
            label_position, label_text = self._get_labels()
            self.index_label.positions = label_position
            self.index_label.labels = label_text
            self.index_range.refresh()

    traits_view = View(Group(Item('history')),
                       Item('component', editor=ComponentEditor(), show_label=False))

