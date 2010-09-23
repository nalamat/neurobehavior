from __future__ import with_statement
import re

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
def convert(name, space='_'):
    s1 = first_cap_re.sub(r'\1'+space+r'\2', name)
    return all_cap_re.sub(r'\1'+space+r'\2', s1).lower()

#from util.binary_funcs import bin
import crc

import threading
import numpy as np
from xml.etree import ElementTree as ET

class Serializable(object):

    def xml(self, node=None):
        if node is None:
            node = ET.Element('TrialBlock')
        for i in self.save:
            if i.endswith('.'):
                section_name = i[:-1]
                section_obj = getattr(self, section_name)
                section = ET.SubElement(node, section_name)
                section.set('type', section_obj.__class__.__name__)
                try:
                    section_obj.xml(section)
                except:
                    pass
            else:
                element = ET.SubElement(node, i)
                el_value = getattr(self, i)
                el_type = str(type(el_value)).split("'")[1]
                element.set('type', el_type)
                if np.iterable(el_value) and not el_type=='str':
                    text = ','.join([str(e) for e in el_value])
                else:
                    text = str(el_value)
                element.text = text
        return ET.ElementTree(node)

    def savexml(self, filename='test.xml'):
        with open(filename, 'w') as f:
            tree = self.xml()
            tree.write(f)

class TaskThread(threading.Thread):
    """Thread that executes a task every N seconds"""
    
    def __init__(self, interval, callable, *args, **kwargs):
        threading.Thread.__init__(self)
        self._finished = threading.Event()
        self._interval = interval
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
    
    def setInterval(self, interval):
        """Set the number of seconds we sleep between executing our task"""
        self._interval = interval
    
    def shutdown(self):
        """Stop this thread"""
        self._finished.set()
    
    def run(self):
        while 1:
            if self._finished.isSet(): return
            self.callable(*self.args, **self.kwargs)
            # sleep for interval or until shutdown
            self._finished.wait(self._interval)

import ConfigParser

def generate_config(obj):

    def parse(section, obj, config):
        for k, v in obj.__getstate__().items():
            try: 
                config.add_section(k)
                parse(k, v, config)
            except AttributeError:
                config.remove_section(k)
                config.set(section, k, v)
        return config

    config = ConfigParser.ConfigParser()
    config.add_section('main')
    return parse('main', obj, config)

def write_config(obj, fname):
    with open(fname, 'w') as f:
        config = generate_config(obj)
        config.write(f)

def test_serializer():
    import paradigm
    paradigm.Paradigm().savexml()

if __name__ == '__main__':
    test_serializer()
