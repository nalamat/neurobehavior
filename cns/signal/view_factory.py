from enthought.traits.api import HasTraits, Instance
from enthought.traits.ui.api import Item, View

def _trait_label(trait):
    if trait.unit is not None: return '%s (%s)' % (trait.label, trait.unit)
    else: return trait.label

def _signal_view_items(signal, prepend='', include_variable=True):
    items = []
    if include_variable:
        items.append('variable')
    # This is not really working yet.  I'm not sure if I want to implement it.
    #if 'base_signal' in signal.class_trait_names():
    #    base_class = signal.class_traits()['base_signal'].trait_type.klass
    #    items = _signal_view_items(signal, prepend='object.base_signal')
    #    items.append(Group(Items, name='test'))

    # List the non-configurable parameters that are modified based on feedback
    # from the other parameters.
    for name, trait in signal.class_traits(configurable=False).items():
        item = Item(prepend+name, label=_trait_label(trait), style='readonly')
        items.append(item)

    # We track whether the parameter is a variable via the trait metadata.  The
    # UI makes the instance available via the name 'object' when calling eval.
    for name, trait in signal.class_traits(configurable=True).items():
        #enabled = "not object.trait('%s').variable" % name
        #enabled = '"%s" not in variables' % name
        enabled = '"%s" != variable' % name
        item = Item(prepend+name, label=_trait_label(trait),
                    enabled_when=enabled)
        items.append(item)
    return items

def signal_view_factory(signal, prepend='', include_variable=True):
    return View(*_signal_view_items(signal, prepend, include_variable))

def signal_class_view_factory(signal, prepend=''):
    # Use if you want to wrap this into a "View" object for MVC separation.
    items = _signal_view_items(signal, prepend)
    properties = dict(signal=Instance(signal.__class__, signal))
    properties['traits_ui_view'] = View(*items)
    klass_name = signal.__class__.__name__ + 'View'
    return type(klass_name, (HasTraits,), properties)()
