import re
import tables
import logging
from datetime import datetime

from cns import get_config

time_fmt = get_config('TIME_FORMAT')
time_pattern = re.compile(r'\d{4}_(\d{2}_?){5}')

log = logging.getLogger(__name__)

name_lookup = {'group':     'Group',
               'earray':    'EArray',
               'array':     'Array',
               'table':     'Table'}

def get_or_append_node(node, name, type='group', *arg, **kw):
    try:
        # TODO: add type checking?
        return getattr(node, name)
    except tables.NoSuchNodeError:
        return append_node(node, name, type, *arg, **kw)

def append_node(node, name, type='group', *arg, **kw):
    log.debug('appending %r to node %r', name, node._v_pathname)
    file = node._v_file
    path = node._v_pathname
    type = name_lookup[type.lower()]
    func = getattr(file, 'create' + type)
    new_node = func(path, name, *arg, **kw)
    return new_node

def extract_date_from_string(string):
    time_string = time_pattern.search(string).group()
    return datetime.strptime(time_string, time_fmt)

def extract_date_from_name(node, pre=None, post=None):
    time_string = time_pattern.find(node._v_name).group()
    return datetime.strptime(time_string, time_fmt)
