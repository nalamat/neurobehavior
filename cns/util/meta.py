"""
This module defines various utility classes and functions for meta-programming.
"""

def update_meta (self, other):
    self.__name__ = other.__name__
    self.__doc__ = other.__doc__
    self.__dict__.update(other.__dict__)
    return self

class LateBindingProperty (property):

    def __new__(cls, fget=None, fset=None, fdel=None, doc=None):

        if fget is not None:
            def __get__(obj, objtype=None, name=fget.__name__):
                fget = getattr(obj, name)
                return fget()

            fget = update_meta(__get__, fget)

        if fset is not None:
            def __set__(obj, value, name=fset.__name__):
                fset = getattr(obj, name)
                return fset(value)

            fset = update_meta(__set__, fset)

        if fdel is not None:
            def __delete__(obj, name=fdel.__name__):
                fdel = getattr(obj, name)
                return fdel()

            fdel = update_meta(__delete__, fdel)

        return property(fget, fset, fdel, doc)
