"""These are additions to facilitate storing and setting of datetime types in
traited classes from numpy arrays containing datetime types.  This is extremely
useful for the functions that store the data using the HDF5 library because they
convert the lists to Numpy record arrays to facilitate storing in the HDF5 file.
"""

from enthought.traits.api import Tuple, TraitType
from datetime import date
import logging
log = logging.getLogger(__name__)

class CTuple(Tuple):

    def validate(self, object, name, value):
        if not isinstance(value, tuple):
            try:
                value = tuple(value)
            except (ValueError, TypeError):
                value = (value, )
        return super(CTuple, self).validate(object, name, value)

class CDate(TraitType):

    def validate(self, object, name, value):
        if isinstance(value, date):
            return value
        try:
            # numpy datetime object has item() method to return datetime
            # instance
            return value.item()
        except: pass
        self.error(object, name, value)