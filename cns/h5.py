
'''
Created on Jul 20, 2010

@author: Brad Buran

Code dependencies
=================

pandas
    Provides a R-style DataFrame object that can facilitate data analysis.
joblib
    Caches function results.  Used to speed up loading and aggregating data from
    the HDF5 files.
    
In general, joblib is pretty good at detecting when the cache is invalid.
However, sometimes you need to manually force the cache to clear.  The function
extract_data (which loads data from the HDF5 file) uses joblib to cache its
results.  To clear the cache::

    >>> from cns import h5
    >>> h5.memory.clear()
    
Before you can understand how the code works, you need to understand a little
about how the HDF5 data structure is represented in Python.  PyTables has a
really nice API (application programming interface) that we can use to access
the nodes stored in the file.  First, open a handle to the file::

    >>> fh = tables.openFile('filename', 'r')

The top-level node can be accessed via an attribute called root::

    >>> root = fh.root

A child node can be accessed via it's name::

    >>> animal = fh.root.Cohort_0.animals.Animal_0

Alternatively, you can request the pathname::

    >>> animal = fh.getNode('/Cohort_0/animals/Animal_0')

The attributes of the animal are stored in a special node called _v_attrs.  This
is a PyTables-specific feature, other HDF5 libraries may have different ways of
accessing the attribute.  These attributes are the same ones you see when
selecting "show properties" from the context menu and selecting the "attributes"
tab.  There are several ways to access the attributes::

    >>> nyu_id = fh.root.Cohort_0.animals.Animal_0._v_attrs.nyu_id

    - or -

    >>> nyu_id = fh.root.Cohort_0.animals.Animal_0._v_attrs['nyu_id']

    - or -

    >>> animal = fh.getNode('/Cohort_0/animals/Animal_0')
    >>> nyu_id = animal.getAttr('nyu_id')

    - or -

    >>> animal = fh.getNode('/Cohort_0/animals/Animal_0')
    >>> nyu_id = animal._v_attrs.nyu_id
'''

import re
import tables
import logging
from datetime import datetime
from pandas import DataFrame
from os import path

# Set up the caching system
try:
    from joblib import Memory
    from tempfile import gettempdir
    temppath = path.join(gettempdir(), 'sane_analysis')
    memory = Memory(temppath)
except ImportError:
    print 'WARNING: joblib module not found, caching will be disabled'
    # This is a mock class decorator that will be used in lieu of the actual
    # joblib.Memory class.  This basically is a decorator that passes through
    # the "decorated" function rather than returning a wrapper.
    class Memory:
        def cache(self, func=None, ignore=None, verbose=None, mmap_mode=False):
            print 'getting called', self, func
            return func
    memory = Memory()

log = logging.getLogger(__name__)

def rgetattr_or_none(obj, xattr):
    '''
    Attempt to load the value of xattr, returning None if the attribute does not
    exist.
    '''
    try:
        return rgetattr(obj, xattr)
    except AttributeError:
        return None

time_fmt = '%Y_%m_%d_%H_%M_%S'
time_pattern = re.compile(r'\d{4}_(\d{2}_?){5}')

def extract_date_from_string(string):
    time_string = time_pattern.search(string).group()
    return datetime.strptime(time_string, time_fmt)

def _parse_xattr(xattr):
    xattr = xattr.replace('../', '/_v_parent/') # replace ../ with _v_parent
    xattr = xattr.replace('+', '/_v_attrs/')    # replace + with _v_attrs
    xattr = xattr.replace('//', '/')            # remove double slashes
    xattr = xattr.replace('/', '.')             # convert to attribute access
    xattr = xattr.replace('<.', '<')
    xattr = xattr.strip('.')                    # remove leading period
    return xattr

def _getattr(obj, xattr):
    if xattr.startswith('<'):
        return _find_ancestor(obj, xattr[1:])
    else:
        return getattr(obj, xattr)

def _rgetattr(obj, xattr):
    try:
        base, xattr = xattr.split('.', 1)
        obj = _getattr(obj, base)
        return _rgetattr(obj, xattr)
    except Exception, e:
        return _getattr(obj, xattr)

def _find_ancestor(obj, xattr):
    if obj == obj._v_parent:
        raise AttributeError, "{} not found".format(xattr)
    try:
        return _rgetattr(obj._v_parent, xattr)
    except AttributeError:
        return _find_ancestor(obj._v_parent, xattr)

def rgetattr(node, xattr):
    '''
    Recursive extended getattr that works with the PyTables HDF5 hierarchy

    ../
        Move to the parent
    /name
        Move to the child specified by name
    <ancestor_name
        Find the nearest ancestor whose name matches ancestor_name
    <+attribute
        Find the nearest ancestor that has the specified attribute
    +attribute
        Get the value of the attribute

    _v_name
        Name of the current node
    ../_v_name
        Name of the parent node
    ../../_v_name
        Name of the grandparent node
    paradigm+bandwidth
        Value of the bandwidth attribute on the child node named 'paradigm'
    ../paradigm+bandwidth
        Value of the bandwidth attribute on the sibling node named 'paradigm'
        (i.e. check to see if the parent of the current node has a child node
        named 'paradigm' and get the value of bandwidth attribute on this child
        node).

    Given the following HDF5 hierarchy::

        Animal_0
            _v_attrs
                sex = F
                nyu_id = 132014
            Experiments
                Experiment_1
                    _v_attrs
                        start_time = August 8, 2011 11:57pm
                        duration = 1 hour, 32 seconds
                    paradigm
                        _v_attrs
                            bandwidth = 5000
                            center_frequency = 2500
                            level = 60 (a)
                    data
                        trial_log
                        contact_data

    >>> node = root.Animal_0.Experiments.Experiment_1.data.trial_log
    >>> xgetattr(node, '../')
    data
    >>> xgetattr(node, '../..')
    Experiment_1
    >>> xgetattr(node, '../paradigm/+bandwidth')
    5000
    >>> xgetattr(node, '<+nyu_id')
    132014
    '''
    xattr = _parse_xattr(xattr)
    if xattr.startswith('<'):
        return _find_ancestor(node, xattr[1:])
    return _rgetattr(node, xattr)

def node_match(n, filter):
    '''
    Checks for match against each keyword.  If an attribute is missing or any
    match fails, returns False.

    Filter can be a dictionary or list of tuples.  If the order in which the
    filters are applied is important, then provide a list of tuples.
    '''
    # If filter is a dictionary, convert it to a sequence of tuples
    if type(filter) == type({}):
        filter = tuple((k, v) for k, v in filter.items())

    # If user only provided one filter rather than a sequence of filters,
    # convert it to a sequence of length 1 so the following loop can handle it
    # better
    if len(filter[0]) == 1:
        filter = (filter,)

    for xattr, criterion in filter:
        try:
            value = rgetattr_or_none(n, xattr)
            if not criterion(value):
                return False
        except AttributeError:
            return False
        except TypeError:
            if not (value == criterion):
                return False
    return True

def walk_nodes(where, filter, classname=None, wildcards=None):
    '''
    Starting at the specifide node, `walk_nodes` visits each node in the
    hierarchy, returning a list of all nodes that match the filter criteria.

    Filters are specified as a sequence of tuples, (attribute, filter).  As
    each node is visited, each filter is called with the corresponding value of
    its attribute.  The node is discarded if it is missing one or more of the
    filter attributes.

    Each filter may be a callable that returns a value or raises an exception.
    If the filter raises an exception or returns an object whose truth value
    is Fales, the node is discarded.

    Attributes may be specified relative to the nodes of interest using the '/'
    POSIX-style path separator.

    Attribute examples:

        _v_name
            Name of the current node
        ../_v_name
            Name of the parent node
        ../../_v_name
            Name of the grandparent node
        paradigm/+bandwidth
            Value of the bandwidth attribute on the child node named 'paradigm'
        ../paradigm/+bandwidth
            Value of the bandwidth attribute on the sibling node named
            'paradigm' (i.e. check to see if the parent of the current node has
            a child node named 'paradigm' and get the value of bandwidth
            attribute on this child node).

    If you have ever worked with pathnames via the command line, you may
    recognize that the path separators work in an identical fashion.

    Filter examples:

        ('_v_name', re.compile('^\d+.*').match) 
            Matches all nodes whose name begins with a sequence of numbers

        ('_v_name', 'par_info')
            Matches all nodes whose name is exactly 'par_info'

        ('..start_time', lambda x: (strptime(x).date()-date.today()).days <= 7)
            Matches all nodes whose grandparent (two levels up) contains an
            attribute, start_time, that evaluates to a date that is within the
            last week.  Useful for restricting your analysis to data collected
            recently.

    Valuable node attributes:

        _v_name
            Name of the node
        _v_pathname
            HDF5 pathname of the node
        _v_depth
            Depth of the node relative to the root node (root node depth is 0)

    If all of the attributes are found for the given node and the attribute
    values meet the filter criterion, the node is added to the list.

    To return all nodes with the attribute klass='Animal'
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> filter = ('_v_attrs.klass', 'Animal')
    >>> iterator = walk_nodes(fh.root, filter)
    >>> animal_nodes = list(iterator)

    To return all nodes who have a subnode, data, with the attribute 'klass'
    whose value is a string beginning with 'RawAversiveData'.
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> base_node = fh.root.Cohort_0.animals.Animal_0.experiments
    >>> filter = ('data.klass', re.compile('RawAversiveData.*').match)
    >>> experiment_nodes = list(walk_nodes(base_node, filter))

    To return all nodes whose name matches a given pattern
    >>> fh = tables.openFile('example_data.h5', 'r')
    >>> filter = ('_v_name', re.compile('^Animal_\d+').match)
    >>> animal_nodes = list(walk_nodes(fh.root, filter))
    '''
    for node in where._f_walkNodes(classname=classname):
        if node_match(node, filter):
            yield node

LINK_CLASSES = tables.link.SoftLink, tables.link.ExternalLink

def p_get_node(node, pattern, dereference=True):
    '''
    Load a single node based on a indeterminate path

    Used to obtain a node when you know that there is one (and only one) node
    that can be reached by the specified pattern.  The pattern may contain
    wildcards to indicate that the name of the intermediate node is unknown.

    If multiple nodes match the wildcard pattern, only the first one found will
    be returned.

    In this example, the file only containes a single physiology experiment.
    However, the parent node is PositiveDTCL_2011_09_09_11_59_58.  You would not
    know what the exact name of this node is without checking it first.

    >>> fh = tables.openFile('110909_G1_tail_behavior_raw.hd5', 'r')
    >>> trial_log = p_load_node(fh.root, '*/data/trial_log')
    '''
    return list(p_load_nodes(node, pattern, dereference))[0]

def p_load_nodes(node, pattern, dereference=True):
    '''
    TODO (document)
    '''
    if type(pattern) != type([]):
        pattern = pattern.split('/')

    # Check to see if the node is a SoftLink or ExternalLink.  If so, get the
    # actual node that the link points to by dereferencing (see the PyTables
    # documentation for an explanation of this).
    if dereference and isinstance(node, LINK_CLASSES):
        node = node()

    if len(pattern) == 0:
        yield node
    elif '*' == pattern[0]:
        for n in node._f_iterNodes():
            for n in p_load_nodes(n, pattern[1:]):
                yield n
    else:
        n = node._f_getChild(pattern[0])
        for n in p_load_nodes(n, pattern[1:]):
            yield n

def p_list_nodes(file_name, pattern, dereference=True):
    '''
    When you know the structure of your datafile (and it is well-formed), then
    this function will be significantly faster than walk_nodes.

    You must process each node as they are loaded.  Once the generator is
    exhausted, the file will be closed and you will be unable to access the data
    stored in the node.
    '''
    with tables.openFile(file_name, 'r') as fh:
        pattern = pattern.split('/')
        if pattern[0] != '':
            raise ValueError, 'Pattern must begin with /'
        for node in load_nodes(fh.root, pattern[1:]):
            yield node

@memory.cache(ignore=('file_name',))
def _extract_data(file_name, filters, fields=None, summary=None,
                  classname='Table', hash='', mode='walk'):
    '''
    Not meant for direct use.  This is broken out of :func:`extract_data` so we
    can wrap the code in a caching decorator to speed up loading of data from
    disk.  The hash is created by :func:`extract_data` to ensure that the cache
    is cleared if the last modified time changes.  Note that if you move the
    file to a different folder, this does not clear the cache.
    '''
    log.info('... No cached copy of data found, reloading data')
    with tables.openFile(file_name, 'r') as h:
        data = DataFrame()
        if mode == 'walk':
            iterator = walk_nodes(h.root, filters, classname)
        else:
            iterator = p_load_nodes(h.root, filters)

        for node in iterator:
            log.info('... Found node %s', node._v_pathname)
            if type(node) == tables.Table:
                # Node is a HDF5 table.  Table.read() returns a Numpy record
                # array (a data structure that is essentially an array with
                # named columns and nested data structures).  We convert this
                # record array into a DataFrame and add some metadata about
                # where it came from.
                frame = DataFrame.from_records(node.read())
                frame['_path'] = node._v_pathname
                frame['_source'] = node._v_name

                if fields is not None:
                    # rgetattr (i.e. "recursive get attribute") is a special
                    # function I wrote that can recursively traverse the
                    # object hierarchy and return the value of the given
                    # attribute.
                    for attr, name in fields:
                        frame[name] = rgetattr_or_none(node, attr)

                if summary is not None:
                    for name, func in summary:
                        frame[name] = func(frame, node)

                data = data.append(frame, ignore_index=True)
            else:
                raise NotImplementedError
    return data

def extract_data(input_files, filters, fields=None, summary=None,
                 classname='Table'):
    '''
    Extracts the data you want into a DataFrame, flattening the HDF5 hierarchy
    in the process.  This results in what is, essentially, a spreadsheet or
    denormalized table.

    Note that data extraction is only supported for nodes of type Table at the
    moment.  I'm not really sure whether it makes sense to support other node
    types as well.

    .. note:: 

        This function calls :func:`_extract_data` for each file.  If
        _extract_data has been called before with this file using the same
        parameters (i.e. filters, fields and summary), a cached copy of the data
        will be returned.  If the filename or last modified timestamp of the
        file has changed, the cache will be cleared.

        Caching significantly speeds up data analysis because loading the data
        from disk is one of the biggest bottlenecks in the analysis pipeline.

    Parameters
    ----------
    input_files : string (single filename) or list (multiple filenames)
        A file or list of HDF5 files to extract data from

    filters : [(string, filter), ...]
        List of (xattr, filter) tuples.  The value of the attribute is extracted
        from the candidate table.  If it passes the filter criterion, the table
        is included in the list of tables to concatenate and return.  The filter
        must be sufficiently strict that it only matches one table type.  Don't
        try to merge the par_info table with the trial_log table.  The tables
        that match the filter are then concatenated.  See :func:`_walk` for
        examples of filters that can be used.

    fields : [(string, string), ...]
        List of (xattr, column_name) tuples which will extract the xattr value
        (relative to the node) and assign the value to column_name in the
        DataFrame.

    summary : [(string, callable), ...]
        List of (name, function) tuples that generate either a single value or
        an array of values of len(frame) that is appended to the DataFrame
        extracted from the current node.  The function must take two arguments,
        the current DataFrame being examined and the current node.  The frame
        will already contain the contents of the current node plus the extra
        attributes specified in fields.

        Note that the summary function must fail gracefully (if desired)
        otherwise the exception will propagate up the hierarchy.

    classname : { 'Table' }
        Only 'Table' is supported for now

    Typical HDF5 file structure
    ---------------------------
    Cohort_{number}
        _v_attrs
            description
        animals
            Animal_{number}
                _v_attrs
                    nyu_id
                    identifier (e.g. tail, fluffy)
                    parents
                    birth
                    sex
                experiments
                    PositiveDTExperiment_{date_time}
                        _v_attrs
                            start_time
                            stop_time
                            date
                            duration
                        data
                            _v_attrs
                                clip
                                nogo_trial_count
                                go_trial_count
                                OBJECT_VERSION (incremented when format changes)
                            contact
                                poke_TTL
                                    _v_attrs
                                        fs (sampling frequency)
                                spout_TTL
                                    _v_attrs
                                        fs (sampling frequency)
                                {et cetera}
                            par_info
                            trial_log
                            water_log
                            {et cetera}
                        paradigm
                            _v_attrs
                                {list of all relevant paradigm attributes}
    
    Give the following::

        filters = (('_v_name', 'trial_log'),
                   ('<+nyu_id', lambda id: id != 0),)

        fields  = (('<+identifier', 'id'),
                   ('<+sex', 'sex'))

        # Assume that pathname points to the directory containing the cohort
        # files to be analyzed.  We need to get a list of all files in that
        # directory that match the pattern *.cohort.hd5.

        from glob import glob
        from os import path
        files = glob(path.join(pathname, '*.cohort.hd5'))
        data = extract_data(files, filters, fields)

    With a HDF5 file containing following structure:

        Animal_0
            _v_attrs
                identifier = Fluffy
                sex = M
                nyu_id = 178320
            experiments
                Experiment
                    _v_attrs
                        start_time
                        end_time
                        duration
                    data
                        trial_log (parameter, trial_type, response)
                            parameter_1, trial_type_1, response_1
                            parameter_2, trial_type_2, response_2
                            parameter_3, trial_type_3, response_3
                            parameter_4, trial_type_4, response_4
                            parameter_5, trial_type_5, response_5
                        contact
                            poke_TTL
                            spout_TTL
                            ...
                    paradigm
        Animal_1
            _v_attrs
                identifier = Tail
                sex = F
                nyu_id = 178321
            experiments
                Experiment
                    _v_attrs
                        start_time
                        end_time
                        duration
                    data
                        trial_log (parameter, trial_type, response)
                            parameter_1, trial_type_1, response_1
                            parameter_2, trial_type_2, response_2
                            parameter_3, trial_type_3, response_3
                            parameter_4, trial_type_4, response_4
                            parameter_5, trial_type_5, response_5
                        contact
                            poke_TTL
                            spout_TTL
                            ...
                    paradigm
        Animal_3
            _v_attrs
                identifier = Tail
                sex = F
                nyu_id = 0
            experiments
                Experiment
                    _v_attrs
                        start_time
                        end_time
                        duration
                    data
                        trial_log (parameter, trial_type, response)
                            parameter_1, trial_type_1, response_1
                            parameter_2, trial_type_2, response_2
                            parameter_3, trial_type_3, response_3
                            parameter_4, trial_type_4, response_4
                            parameter_5, trial_type_5, response_5
                        contact
                            poke_TTL
                            spout_TTL
                            ...
                    paradigm

    The result will be a DataFrame containing the following columns:

        id          sex  parameter      trial_type  response

    With the following data:

        Fluffy      M    0              'NOGO'      'spout'
        Fluffy      M    20             'GO'        'spout'
        Fluffy      M    10             'GO'        'spout'
        Fluffy      M    40             'GO'        'poke'
        Fluffy      M    0              'NOGO'      'poke'
        Tail        F    0              'NOGO'      'poke'
        Tail        F    0              'NOGO'      'spout'
        Tail        F    20             'GO'        'spout'
        Tail        F    40             'GO'        'poke'
        Tail        F    10             'GO'        'spout'

    Once extracted, these records can be indexed by column name and row::

        >>> print data['sex']
        ['M', 'M', 'M', 'M', 'M', 'F', 'F', 'F', 'F', 'F']

        >>> print data[:3]['parameter']
        [0, 20, 10]

        >>> mask = data['parameter'] == 40
        >>> print data[mask][['id', 'response']]
        [['Fluffy', 'poke'],
         ['Tail',   'poke']]

    To save the extracted data to a tab-delimited file::
        
        >>> data.to_csv(filename, sep='\t')

    See the docstring for pandas.DataFrame.to_csv for additional information
    on the arguments that can be used for saving data to a file.

    Understanding how the list of tuples passed to summary is a little more
    complicated.  The callable (e.g. a Python function) is provided with two
    arguments, the DataFrame (which contains the data extracted from the table)
    and the actual table node itself.  Given the following function::

        def score_contact(frame, node, offset, duration):
            # The trial start timestamp (in cycles)
            timestamps = frame['ts_start']

            # contact_digital is a boolean array indicating whether the subject
            # was in contact with the spout on that given sample.
            contact = node._v_parent.contact.contact_digital
            fs = contact._v_attrs.fs

            # Extract the last 100 msec of the contact data for each trial trial
            # and compute the fraction of the time the subject was in contact
            # with the spout.
            lb = int(offset*fs)
            ub = int(duration*fs)

            # The following line of code is known as a list comprehension.  It
            # is functionally equivalent to
            #
            # result = []
            # for ts in timestamps:
            #     x = contact[ts+lb:ts+ub].mean()
            #     result.append(x)
            # return result

            return [contact[ts+lb:ts+ub].mean() for ts in timestamps]

    By default, the aversive paradigm computes the "contact fraction" as the
    last 100 msec of the trial.  Let's say we wish to use a different criterion
    when scoring the data (e.g. we want to look at the last 250 msec instead).

    First, let's freeze the offset and duration arguments so that the function
    defaults to the last 250 msec of the trial.  For this purpose, we use a very
    useful function included in the standard Python library, functools.partial.

        >>> from functools import partial
        >>> contact_250 = partial(score_contact, 0.750, 0.250)

    We've just created a new function, `contact_250`, which is identical to
    `score_contact` except the values of the last two arguments (offset and
    duration) are now permanently set to 0.750 and 0.250, respectively.  We are
    also interested in the fraction of time the subject was in contact with the
    spout during the entire trial.  Let's create another function that will
    compute this fraction::

        >>> contact_1000 = partial(score_contact, 0.0, 1.0)

    Now, let's go back to our original arguments to extract_data and add one
    more::

        filters = (('_v_name', 'trial_log'),
                   ('<+nyu_id', lambda id: id != 0),)

        fields  = (('<+identifier', 'id'),
                   ('<+sex', 'sex'),)

        summary = (('contact_250', contact_250),
                   ('contact_1000', contact_1000),) 

        from glob import glob
        from os import path
        files = glob(path.join(pathname, '*.cohort.hd5'))
        data = extract_data(files, filters, fields, summary)

    As `extract_data` process each trial_log node, it will call the two
    functions, `contact_250` and `contact_1000`, with the DataFrame
    (representing the data extracted from that specific trial log) along with
    the actual trial_log HDF5 node.  This means that your function has access to
    both the trial log data plus just about any data contained in the HDF5 file.
    As you can see in the code for `score_contact`, it is pulling the trial
    timestamps out of the 'ts_start' column in the DataFrame and locating the
    contact data associated with that particular experiment.  It returns an
    array of contact scores for each trial.

    The resulting DataFrame will now contain the following columns::

        id     sex  parameter trial_type  response contact_250 contact_1000

    With the following data::

        Fluffy M    0         'NOGO'      'spout'  0.1         0.32
        Fluffy M    20        'GO'        'spout'  0.11        0.32
        Fluffy M    10        'GO'        'spout'  0.21        0.32
        Fluffy M    40        'GO'        'poke'   0.43        0.32
        Fluffy M    0         'NOGO'      'poke'   0.13        0.44 
        Tail   F    0         'NOGO'      'poke'   0.33        0.54
        Tail   F    0         'NOGO'      'spout'  0.3         0.32
        Tail   F    20        'GO'        'spout'  0.9         0.32
        Tail   F    40        'GO'        'poke'   0.99        0.65
        Tail   F    10        'GO'        'spout'  0.12        0.32

    .. note::

        This data table is contrived, so the numbers may not make sense if you
        analyze it too critically.

    '''
    # basestring matches both ASCII and Unicode strings
    if isinstance(input_files, basestring):
        input_files = (input_files,)

    # Gather all the data nodes by looking for the nodes in the HDF5 tree that
    # match our filter.  Nodes are HDF5 objects (e.g. either a group containing
    # children objects (Animal.experiments contains multiple experiments) or a
    # table (e.g. the par_info table).  The function walk_nodes is a special
    # function I wrote that interates through every node in the HDF5 file and
    # examins its metadata.  A list of all the nodes whose metadata matches the
    # filter properties are returned.
    data = DataFrame()

    for file_name in input_files:
        log.info('Processing file %s', file_name)

        # Create a unique hash for the file that consists of the final part of
        # the file_name (i.e. excludes the path) and the last time it was
        # modified.  This hash will be used by the joblib.Memory class (which
        # wraps the _extract_data function to determine whether or not it's OK
        # to return a cached version of the data or if the data must be reloaded
        # from disk.  If the file hash changes (e.g. the f, the data will be reloaded.
        file_hash = '{}{}'.format(path.basename(file_name),
                                  path.getmtime(file_name))
        frame = _extract_data(file_name, filters, fields, summary, classname,
                              file_hash)
        frame['_file'] = file_name
        data = data.append(frame, ignore_index=True)

    return data

def create_date_filter(start, end, convert=False):
    '''
    Create a data range filter for `extract_data` that matches all dates falling
    in the range [start, end).

    Parameters
    ----------
    start : date or datetime
        Start date
    end: date or datetime
        End date
    convert : boolean
        Convert string representation of date format to datetime object

    The date filter cannot handle mixed date formats.
    '''

    if convert:
        return lambda d: start <= extract_date_from_string(d) < end
    return lambda d: start <= d < end
