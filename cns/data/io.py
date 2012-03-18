import tables
from cns.data import persistence

import logging
log = logging.getLogger(__name__)

class BadCohortFile(Exception):

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
    except persistence.PersistenceReadError:
        raise BadCohortFile(filename)

def save_cohort(cohort, filename):
    fh = tables.openFile(filename, 'a')
    node = persistence.add_or_update_object(cohort, fh.root)
    fh.close()
    return node
