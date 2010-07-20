import functools
import tables
import re
from numpy import dtype, array
from enthought.traits.api import Array, List, Dict
from cns.channel import FileChannel, FileMultiChannel
import datetime

import logging
log = logging.getLogger(__name__)

def next_id(element, name=''):
    try: next_id = element._f_getAttr(name+'_NEXT_ID')
    except: next_id = 0
    element._f_setAttr(name+'_NEXT_ID', next_id + 1)
    return next_id

def get_np_dtype(trait):
    types = ['object' if t.startswith('date') else t for t in trait.col_types]
    return dtype(zip(trait.col_names, types))

def get_hdf5_dtype(trait):
    types = ['S32' if t.startswith('date') else t for t in trait.col_types]
    return dtype(zip(trait.col_names, types))

def get_traits(object, filter_readonly=False, filter_events=True, **metadata):
    '''Convenience function to filter out readonly traits.  This is useful for
    reconstructing a traited class that has been persisted by avoiding writes
    to a readonly trait.  It is expected that the traited class knows how to
    reconstruct readonly properties.
    '''
    if filter_readonly:
        filter = lambda x: x() is None or x()[1].__name__ <> '_read_only'
        metadata['property'] = filter
    if filter_events:
        metadata['type'] = lambda x: x <> 'event'
    return object.class_traits(**metadata)

def add_or_update_object(object, node, name=None):
    h5_file = node._v_file
    h5_path = node._v_pathname
    base_name = object.__class__.__name__
    #log.debug('%s, %s, %s', h5_file, h5_path, base_name)

    if name is None:
    #if as_child:
        # Check to see if object has been assigned a unique ID
        if not hasattr(object, 'UNIQUE_ID'):
            setattr(object, 'UNIQUE_ID', next_id(node, base_name))
        object_name = base_name + '_' + str(object.UNIQUE_ID)
    else:
        object_name = name

    # Check to see if node has already been set aside for the object
    try:
        object_node = getattr(node, object_name)
    except tables.NoSuchNodeError:
        object_node = h5_file.createGroup(h5_path, object_name)
        # A bit redundant since the name of the node also contains the ID
        try: object_node._f_setAttr('UNIQUE_ID', object.UNIQUE_ID)
        except: pass
        # Info that allows us to recreate the object later

    object_node._f_setAttr('module', object.__class__.__module__)
    object_node._f_setAttr('klass', object.__class__.__name__)
    #else: # We are supposed to use this node!
        #object_node = node

    # Now we add the metadata for the object
    # TODO: add support for deleted metadata.  Right now this is unsupported
    # because we don't need this use case.
    for name, trait in object.class_traits(store='attribute').items():
        # this is a bit of a hack to ensure we get the raw value since we normally get
        # a list or dict back wrapped in a trait object
        value = getattr(object, name)
        if trait.is_trait_type(List):
            value = value[:]
        elif trait.is_trait_type(Dict):
            value = dict(value)

        if value is None:
            value = 'None'
        if value.__class__ in date_classes:
            # The HDF5 datetime datatype requires seconds since the Unix epoch
            # (POSIX time_t).  We just convert the datetime to a string and
            # store it that way instead.  It avoids cross-platform
            # inconsistencies with the POSIX timestamps.
            value = strftime(value)
        object_node._f_setAttr(name, value)

    for name in object.class_trait_names(store='array'):
        value = getattr(object, name)
        try: getattr(object_node, name)._f_remove()
        except tables.NoSuchNodeError: pass
        if len(value)==0:
            # Create a blank array
            atom = tables.atom.Atom.from_dtype(value.dtype)
            h5_file.createEArray(object_node._v_pathname, name, atom, (0,))
        else:
            h5_file.createArray(object_node._v_pathname, name, value)

    # We need to track children nodes now since we will delete any old nodes
    # that the object may no longer have.  All nodes to be protected from
    # deletion must be added to the children list.
    # Actually, I have decided this is a bad idea since it risks losing data
    #children = []
    for name in object.class_trait_names(store='table'):
        # Create copy of value since we may need to convert the datetime series.
        value = array(getattr(object, name))
        trait = object.trait(name)
        # When datteime support is added to Numpy, we can delete the following
        # line and uncomment the line after
        value = sanitize_datetimes(value, trait)
        #value = array(value, dtype=get_np_dtype(trait))
        value = array(value, dtype=get_hdf5_dtype(trait))

        try:
            # Table already exists.  We delete the data in the table and
            # re-add it.  This is not really efficient, but the current use
            # case for this type of table will only have up to 100 rows so
            # we should not see much of a performance hit.
            table = getattr(object_node, name)
            table.truncate(0)
            table.append(value)
        except tables.NoSuchNodeError:
            table = h5_file.createTable(object_node._v_pathname,
                                        name, value)
        #children.append(table)

    # add all existing children
    for name in object.class_trait_names(store='child'):
        value = getattr(object, name)

        try: group_node = getattr(object_node, name)
        except tables.NoSuchNodeError:
            object_path = object_node._v_pathname
            group_node = h5_file.createGroup(object_path, name)

        if hasattr(value, '__iter__'): # This is a list of items
            #children.append(group_node)
            group_children = []
            for v in value:
                child = add_or_update_object(v, group_node)
                group_children.append(child)
            # We need to think about whether we should be deleting records.
            # Maybe just add a deleted attribute so we know not to load the
            # node when the parent object is loaded.
            for child in group_node._v_children.values():
                if child not in group_children:
                    child._f_remove(recursive=True)
        else: # nope, it's not a list, just a single object
            add_or_update_object(value, object_node, name)

    # Ok, remove any children that don't belong (i.e. that were not added or
    # updated)!
    #for child in object_node._v_children.values():
    #    if child not in children:
    #        child._f_remove(recursive=True)

    append_metadata(object, object_node)
    h5_file.flush()
    return object_node

date_classes = [datetime.date, datetime.time, datetime.datetime]

date_fmt = '%Y-%m-%d'
time_fmt = '%H:%M:%S'
datetime_fmt = date_fmt + ' ' + time_fmt
time_splitter = re.compile('[\s:-]+')

def get_date_fmt(resolution='S'):
    datetime_fmt = "%Y-%m-%d %H:%M:%S"
    return datetime_fmt.split(resolution)[0]+resolution

def guess_str_resolution(time_string):
    res = 'YmdHMS'
    index = len(time_splitter.split(time_string))-1
    return res[index]

def guess_datetime_fmt(datetime_val):
    # datetime is a subclass of date, so be sure that we do elif so that the
    # second condition is not evaluated.
    if isinstance(datetime_val, datetime.datetime):
        fmt = datetime_fmt
    elif isinstance(datetime_val, datetime.time):
        fmt = time_fmt
    elif isinstance(datetime_val, datetime.date):
        fmt = date_fmt
    return fmt

def strptime_arr(value, resolution=None):
    if len(value) == 0:
        return value
    if resolution is None:
        resolution = guess_str_resolution(value[0])
    fmt = get_date_fmt(resolution)
    return [datetime.datetime.strptime(v, fmt) for v in value]

def strptime(value, resolution=None):
    if value is None or value == 'None':
        return None
    if resolution is None:
        resolution = guess_str_resolution(value)
    fmt = get_date_fmt(resolution)
    value_datetime = datetime.datetime.strptime(value, fmt)
    if resolution in 'Ymd':
        return value_datetime.date()
    else:
        return value_datetime

def strftime_arr(value, resolution=None):
    if len(value) == 0:
        return value
    if resolution is None:
        fmt = guess_datetime_fmt(value[0])
    else:
        fmt = get_date_fmt(resolution)
    return [v.strftime(fmt) for v in value]

def strftime(value, resolution=None):
    if value is None:
        return 'None'
    if resolution is None:
        fmt = guess_datetime_fmt(value)
    else:
        fmt = get_date_fmt(resolution)
    return value.strftime(fmt)

def switch_datetime_fmt(table, trait, parser):
    # TODO: this is obviously not the most efficient implementation; however,
    # it works!
    if len(table):
        table = [tuple(row) for row in table]
        table = array(table, dtype=get_np_dtype(trait))
        for cname, ctype in zip(trait.col_names, trait.col_types):
            if ctype.startswith('datetime'):
                res = ctype[-2]
                table[cname] = parser(table[cname], res)

        # This is an ugly hack required by Numpy v1.3.  Once datetime support is
        # included in Numpy (possibly v1.5) much of the work can be delegated to
        # Numpy.  Possibly some of the other libraries that depend on numpy
        # (e.g. PyTables) will support it better.
        return [tuple(e) for e in table.tolist()]
    else:
        return table

sanitize_datetimes = functools.partial(switch_datetime_fmt, parser=strftime_arr)
unsanitize_datetimes = functools.partial(switch_datetime_fmt,
        parser=strptime_arr)

def append_metadata(object, source):
    object.store_file = source._v_file.filename # TODO: we need to get abs pathource.
    object.store_path = source._v_pathname
    object.store_name = source._v_name
    object.store_node = source
    return object

def load_object(source, name=None):
    if name is not None:
        source = getattr(source, name)

    kw = {}
    try:
        kw['UNIQUE_ID'] = source._f_getAttr('UNIQUE_ID')
    except AttributeError:
        pass

    module_name = source._f_getAttr('module')
    klass_name = source._f_getAttr('klass')
    #try: version = source._f_getAttr('version')
    #except AttributeError: version = 0.1

    # We need to obtain a reference to the type so we can adequately parse any
    # datetime values that are stored in the HDF5 file.  This type will also be
    # used to create a class instance once we are done loading the data.
    type = getattr(__import__(module_name, fromlist=[klass_name]), klass_name)

    #for name, trait in type.class_traits(store='attribute').items():
    for name, trait in get_traits(type, True,  store='attribute').items():
        value = source._f_getAttr(name)
        # TraitMap will raise an error here
        try:
            klass = trait.trait_type.klass
        except:
            klass = None
        # We just want to check on the datetime
        if klass is not None and klass in date_classes:
            value = strptime(value)
        elif isinstance(value, int):
            value = int(value)

        kw[name] = value

    #for name, trait in type.class_traits(store='table').items():
    for name, trait in get_traits(type, True,  store='table').items():
        # Converts datetime back from string to Python datetime format
        data = getattr(source, name)[:]
        data = unsanitize_datetimes(data, trait)
        kw[name] = data

    #for name, trait in type.class_traits(store='child').items():
    for name, trait in get_traits(type, True, store='child').items():
        value = getattr(source, name)
        if trait.is_trait_type(List) or trait.is_trait_type(Array):
            kw[name] = [load_object(o) for o in value._v_children.values()]
            #kw[name].sort()
        else:
            kw[name] = load_object(value)

    for name, trait in get_traits(type, True, store='automatic').items():
        try:
            try:
                value = getattr(source, trait.store_name)
            except (TypeError, AttributeError):
                value = getattr(source, name)
            kw[name] = value
        except tables.NoSuchNodeError:
            pass

    for name, trait in get_traits(type, True, store='channel').items():
        try:
            try:
                value = getattr(source, trait.store_name)
            except (TypeError, AttributeError):
                value = getattr(source, name)
            kw[name] = load_file_channel(value)
        except tables.NoSuchNodeError:
            pass

    object = type(**kw)
    return append_metadata(object, source)

def load_file_channel(node):
    kw = {}
    kw['fs'] = node._f_getAttr('fs')
    kw['dtype'] = node.atom.dtype
    kw['compression_level'] = node.filters.complevel
    kw['compression_type'] = node.filters.complib
    kw['use_checksum'] = node.filters.fletcher32
    kw['node'] = node._g_getparent()
    kw['buffer'] = node
    kw['name'] = node.name
    
    if len(node.shape) == 2:
        klass = FileMultiChannel
        kw['channels'] = node.shape[1]
    else:
        klass = FileChannel
    return klass(**kw)
