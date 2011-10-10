import tables
import datetime
import unittest

from cns.data.type import Animal, Cohort
from cns.data import persistence
from cns.experiment.paradigm.aversive_paradigm import AversiveParadigm

def create_cohort():
    tail = Animal(sex='F', parents='HH', 
                  birth=datetime.date(2010, 12, 30),
                  weight_log=[(datetime.datetime(2010, 4, 15, 1, 12), 32.1),
                              (datetime.datetime(2010, 4, 16, 2, 24), 34.1),
                              (datetime.datetime(2010, 4, 17, 3, 32), 38.1),
                              (datetime.datetime(2010, 4, 18, 1, 1), 40.1),
                              ])

    return Cohort(description='Test Description', animals=[tail])

class testPersistence(unittest.TestCase):

    def setUp(self):
        self.cohort = create_cohort()
        self.paradigm = AversiveParadigm()
        self.fh = tables.openFile('test.h5', 'a')
        persistence.add_or_update_object(self.cohort, self.fh.root, 'cohort')
        persistence.add_or_update_object(self.paradigm, self.fh.root, 'paradigm')
        
    def assertTraitedObjectsEqual(self, a, b):
        a_values = get_comparable_traits(a)
        b_values = get_comparable_traits(b)
        self.recursive_cmp(a_values, b_values)
        
    def testCohortPersistence(self):
        cohort = persistence.load_object(self.fh.root, 'cohort')
        self.assertTraitedObjectsEqual(self.cohort, cohort)
        
    def testParadigmPersistence(self):
        paradigm = persistence.load_object(self.fh.root, 'paradigm')
        self.assertTraitedObjectsEqual(self.paradigm, paradigm)
        
    def testSubGroup(self):
        animal = self.fh.root.cohort.animals._v_children.values()[0]
        persistence.get_or_append_node(animal, 'foo')
        persistence.add_or_update_object(self.cohort, self.fh.root, 'cohort')
        print self.fh.root.cohort.animals._v_children.values()[0]
        
    def recursive_cmp(self, a, b):
        if isinstance(a, dict):
            for k in a.keys():
                self.recursive_cmp(a[k], b[k])
        elif isinstance(a, (list, tuple)):
            for a_item, b_item in zip(a, b):
                self.recursive_cmp(a_item, b_item)
        else:
            try:
                self.assertAlmostEqual(a, b, 3)
            except TypeError:
                self.assertEqual(a, b)
        
def get_comparable_traits(object):
    if isinstance(object, list):
        return [get_comparable_traits(item) for item in object]
    elif hasattr(object, 'trait_names'):
        traits = object.trait_names()
        traits.remove('trait_added')
        traits.remove('trait_modified')
        attrs = {}
        for trait in traits:
            value = getattr(object, trait)
            attrs[trait] = get_comparable_traits(value)
        return attrs
    else:
        return object

if __name__ == '__main__':
    unittest.main()
