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

def get_traits(object, filter_readonly=False, filter_events=True, **metadata):
    '''Convenience function to filter out readonly traits.  This is useful for
    reconstructing a traited class that has been persisted.  Typically readonly
    traits are properties that the traited class reconstructs from other class
    attributes.
    '''
    if filter_readonly:
        filter = lambda x: x() is None or x()[1].__name__ <> '_read_only'
        metadata['property'] = filter
    if filter_events:
        metadata['type'] = lambda x: x <> 'event'
    return object.class_traits(**metadata)

def store_attribute(node, object, name, trait):
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
    node._f_setAttr(name, value)

def store_array(node, object, name, trait):
    value = getattr(object, name)
    try: getattr(node, name)._f_remove()
    except tables.NoSuchNodeError: pass
    if len(value)==0:
        # Create a blank array
        atom = tables.atom.Atom.from_dtype(value.dtype)
        node._v_file.createEArray(node._v_pathname, name, atom, (0,))
    else:
        node._v_file.createArray(node._v_pathname, name, value)

def store_table(node, object, name, trait):
    # Create copy of value since we may need to convert the datetime series.
    value = array(getattr(object, name))
    trait = object.trait(name)
    # When datteime support is added to Numpy, we can delete the following
    # line and uncomment the line after
    value = sanitize_datetimes(value, trait)
    #value = array(value, dtype=get_np_dtype(trait))
    #value = array(value, dtype=get_hdf5_dtype(trait))
    value = array(value, dtype=trait.dtype)

    try:
        # Table already exists.  We delete the data in the table and
        # re-add it.  This is not really efficient, but the current use
        # case for this type of table will only have up to 100 rows so
        # we should not see much of a performance hit.
        table = getattr(node, name)
        table.truncate(0)
        table.append(value)
    except tables.NoSuchNodeError:
        table = node._v_file.createTable(node._v_pathname, name, value)

def store_child(node, object, name, trait):
    value = getattr(object, name)

    try: group_node = getattr(node, name)
    except tables.NoSuchNodeError:
        object_path = node._v_pathname
        group_node = node._v_file.createGroup(object_path, name)

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
        add_or_update_object(value, node, name)

def add_or_update_object(object, node, name=None):
    '''
    Persists Python object to a node in a HDF5 file.

    When the Python object is saved as a node in a HDF5 file two attributes,
    klass and module, are stored along with the object data.  These attributes
    are used by `load_object` to recreate the original object.

    Parameters
    ==========
    object
        Object to be saved
    node
        HDF5 node to save object data to
    name
        Name of object node that serves as the root of the object data.  The
        object node will be appended to node.  If None, then the node will be
        used as the root for the object data.

    Right now this function only works with subclasses of `HasTraits` since it
    requires some metadata to be set for each trait that is being saved.
    '''

    h5_file = node._v_file
    h5_path = node._v_pathname
    base_name = object.__class__.__name__

    if name is None:
    #if as_child:
        # Check to see if object has been assigned a unique ID
        if not hasattr(object, 'UNIQUE_ID'):
            setattr(object, 'UNIQUE_ID', next_id(node, base_name))
        object_name = base_name + '_' + str(object.UNIQUE_ID)
    else:
        object_name = name

    log.debug('Saving %s to %s in file %s', object_name, h5_path,
              h5_file.filename)

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
    store_map = (('attribute', store_attribute),
                 ('array', store_array),
                 ('table', store_table),
                 ('child', store_child),
                )

    for mode, store in store_map:
        log.debug('Storing %s data', mode)
        for name, trait in object.class_traits(store=mode).items():
            log.debug('Storing %s', name)
            store(object_node, object, name, trait)

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
        try:
            dtype = trait.dtype
        except AttributeError:
            dtype = get_np_dtype(trait)

        table = [tuple(row) for row in table]
        table = array(table, dtype=dtype)

        for cname, ctype in dtype:
            if ctype.startswith('datetime'):
                res = ctype[-2]
                table[cname] = parser(table[cname], res)

        # This is an ugly hack required by Numpy v1.3.  Once datetime support is
        # included in Numpy (possibly v1.5) much of the work can be delegated to
        # Numpy.  Possibly some of the other libraries that depend on numpy
        # (e.g. PyTables) will support it better as well.
        return [tuple(e) for e in table.tolist()]
    else:
        return []

sanitize_datetimes = functools.partial(switch_datetime_fmt, parser=strftime_arr)
unsanitize_datetimes = functools.partial(switch_datetime_fmt,
                                         parser=strptime_arr)

def append_metadata(object, source):
    from os.path import abspath
    object.store_node_source = abspath(source._v_file.filename)
    object.store_node_path = source._v_pathname
    return object

class PersistenceReadError(BaseException):
    '''Unable to recreate persisted object.'''

    mesg = """Attempt to reconstruct object from HDF5 file failed because the
    required metadata (module and classname) are missing.  Source file: %s,
    Object path: %s"""

    def __init__(self, file, path):
        self.path = path
        self.file = file

    def __str__(self):
        return self.mesg % (self.file, self.path)

def load_table(node, name, trait):
    return unsanitize_datetimes(getattr(node, name)[:], trait)

def load_child(node, name, trait):
    value = getattr(node, name)
    if trait.is_trait_type(List) or trait.is_trait_type(Array):
        return [load_object(o) for o in value._v_children.values()]
    else:
        return load_object(value)

def load_automatic(node, name, trait):
    # Traited classes do not properly raise AttributeError but return None
    # instead.
    path = trait.store_path if trait.store_path else name
    return node._f_getChild(path)

def load_channel(node, name, trait):
    try:
        value = getattr(node, trait.store_path)
    except (TypeError, AttributeError):
        value = getattr(node, name)
    return load_file_channel(value)

def load_attribute(node, name, trait):
    value = node._f_getAttr(name)
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
    return value


def get_object(filename, path, *args, **kw):
    '''
    Reconstructs original Python object

    Parameters
    ----------
    filename : string
        File to load object from
    path : string
        Path to object
    *args, **kw
        Arguments to pass to :func:`load_object`

    Returns
    -------
    object

    This function is a loose wrapper around `load_object that opens the
    file then passes the handle to `load_object`, refer to :func:`load_object`
    for more detail.
    '''
    source = tables.openFile(filename, 'r')
    return load_object(source, path, *args, **kw)

def get_objects(filename, path, *args, **kw):
    '''
    Attempt to load all children in a group and return the list

    Parameters
    ----------
    filename : string
        File to load object from
    path : string
        Path to object
    *args, **kw
        Arguments to pass to :func:`load_objects`

    Returns
    -------
    object

    This function is a loose wrapper around `load_objects' that opens the
    file then passes the handle to `load_object`, refer to :func:`load_objects`
    for more detail.
    '''

    source = tables.openFile(filename, 'r')
    return load_objects(source.getNode(path), *args, **kw)

def load_objects(source, filter, child=None, type=None):
    '''
    Attempt to load all children in a group and return the list

    Parameters
    ----------
    source : node
        Open HDF5 node (PyTables format)
    filter : dict
        Dictionary to be passed to :func:`h5_utils.iter_nodes` to filter against
    child : string
        Path relative to the child to be loaded
    '''
    from h5_utils import iter_nodes
    iter = iter_nodes(source, filter)
    if child is not None:
        return [load_object(node._f_getChild(child)) for node in iter]
    else:
        return [load_object(node) for node in iter]

def load_object(source, path=None, type=None):
    '''
    Reconstructs original Python object from a node in an open HDF5 file.

    When a Python object is saved as a node in a HDF5 file, it includes two
    attributes, klass and module, along with the object data.  This function
    imports the class from the specified module and populates it with the data
    in the HDF5 file.  

    This function is meant to be very forgiving.  If data nodes are missing in
    the file, a message is logged but no error is raised.  Earlier versions of
    add_or_update object did not always create the necessary data nodes if the
    class attribute was empty, so it's no surprise that we do not always find
    the expected nodes!

    Readonly traits are *not* loaded.  It is assumed that the class knows how to
    reconstruct readonly values.

    Parameters
    ==========
    source
        HDF5 node
    type
        Datatype of object to be loaded.  If None, the type will be inferred
        from the module_name and klass_name attributes of the node.

    Raises
    ======
    PersistenceReadError
        Raised if there is insufficient information to determine the original
        type of the object.

    Right now this function only works with subclasses of `HasTraits` since it
    requires some metadata to be set for each trait that is being loaded.

    TODO: Create a "dummy" class if we cannot infer the type.  This will allow
    us to load "static" objects without the appropriate class methods.
    '''
    if path is not None and '/' in path:
        node = source.getNode(path)
    elif path is not None:
        node = getattr(source, path)
    else:
        node = source

    kw = {}
    try: kw['UNIQUE_ID'] = node._f_getAttr('UNIQUE_ID')
    except AttributeError: pass

    if type is None:
        # We need to obtain a reference to the type so we can adequately parse
        # any datetime values that are stored in the HDF5 file.  This type will
        # also be used to create a class instance once we are done loading the
        # data.
        try:
            module_name = node._v_attrs.module
            klass_name = node._v_attrs.klass
            module = __import__(module_name, fromlist=[klass_name])
            type = getattr(module, klass_name)
        except AttributeError:
            raise PersistenceReadError(node._v_file.filename, node._v_pathname)

    loaders = (('channel', load_channel),
               #('node', load_node),
               ('automatic', load_automatic),
               ('child', load_child),
               ('table', load_table),
               ('attribute', load_attribute),
              )

    for mode, load in loaders:
        log.debug('Loading data stored as %s', mode)
        for name, trait in get_traits(type, True, store=mode).items():
            log.debug('Loading %s', name)
            try:
                kw[name] = load(node, name, trait)
            except tables.NoSuchNodeError:
                log.warn('Node %s from file %s does not have node "%s"',
                          node._v_pathname, node._v_file.filename, name)
            except AttributeError:
                log.warn('Node %s from file %s does not have attribute "%s"',
                         node._v_pathname, node._v_file.filename, name)

    object = type(**kw)
    return append_metadata(object, node)

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
