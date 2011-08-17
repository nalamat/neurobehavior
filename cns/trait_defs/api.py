'''
Created on May 4, 2010

@author: Brad
'''

def Alias(name):
    return Property(lambda obj: getattr(obj, name),
                    lambda obj, val: setattr(obj, name, val))
