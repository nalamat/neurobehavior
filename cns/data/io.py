import tables
from cns.data.type import Animal, Cohort
from cns.data import persistence

import logging
log = logging.getLogger(__name__)

class BadCohortFile(BaseException):

    def __init__(self, file):
        self.file = file

    def __str__(self):
        return '%s file is not a cohort data file or has been corrupted' \
                % self.file

def load_cohort(id, filename):
    """Right now we just store a single cohort in a HDF5 file.  This may change 
    in the future though."""
    try:
        fh = tables.openFile(filename, 'r')
        obj = persistence.load_object(getattr(fh.root, 'Cohort_' + str(id)))
        fh.close()
        return obj
    except persistence.PersistenceReadError, e:
        raise BadCohortFile(filename)

def save_cohort(cohort, filename):
    fh = tables.openFile(filename, 'a')
    node = persistence.add_or_update_object(cohort, fh.root)
    #fh.flush()
    fh.close()
    return node

if __name__ == '__main__':
    import datetime
    file = tables.openFile('test.h5', 'a')
    try:
        a = Animal(parents='HH', birth=datetime.date(2009, 11, 30),
                   identifier='tail')
        a.weight_log.append((datetime.date.today(), 32.0))
        a.weight_log.append((datetime.date.today(), 34.0))
        a.weight_log.append((datetime.date.today(), 65.0))
        a.status_log.append((datetime.date.today(), 'ON WATER'))
        a.status_log.append((datetime.date.today(), 'OFF WATER'))
        a.status_log.append((datetime.date.today(), 'OFF WATER'))
        #add_or_update_animal(a, file.root)
        c = Cohort(animals=[a], description='Test Cohort')
        add_or_update_object(c, file.root)
    #cohort = Cohort(animals=[Animal(parents='HH', 
    #                                birth=datetime.date(2009, 11, 30),
    #                                identifier='tail')])
    #file = save_cohort(cohort, file)
    finally: file.close()
    file = tables.openFile('test.h5', 'a')
