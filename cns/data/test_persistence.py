import tables
import datetime
import unittest

from cns.data.type import Animal, Cohort
from cns.data import persistence

def create_cohort():
    tail = Animal(id=100, sex='F', parents='HH', 
                  birth=datetime.date(2010, 12, 30),
                  weight_log=[(datetime.date(2010, 4, 15), 32.1),
                              (datetime.date(2010, 4, 16), 34.1),
                              (datetime.date(2010, 4, 17), 38.1),
                              (datetime.date(2010, 4, 18), 40.1),
                              ])

    return Cohort(description='Test Description', animals=[tail])

class testPersistence(unittest.TestCase):

    def setUp(self):
        self.cohort = create_cohort()
        self.fh = tables.openFile('test.h5', 'w')

    def testPersistence(self):
        persistence.add_or_update_object(self.cohort, self.fh.root)

if __name__ == '__main__':
    unittest.main()
