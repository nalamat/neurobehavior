import numpy as np

def flatten_dtype(dtype, prepend=''):
    new_descr = []
    descr = dtype.descr if type(dtype) != type([]) else dtype
    for name, value in descr:
        base_name = prepend + name
        if type(value) == type([]):
            sub_dtype = flatten_dtype(value, base_name + '.')
            new_descr.extend(sub_dtype.descr)
        else:
            new_descr.append((base_name, value))
    return np.dtype(new_descr)

def flatten_recarray(r):
    flattened_dtype = flatten_dtype(r.dtype)
    return r.view(flattened_dtype)
