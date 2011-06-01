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

def cluster(r, groupby, sort=None):
    rowd = dict()
    for i, row in enumerate(r):
        key = tuple([row[attr] for attr in groupby])
        rowd.setdefault(key, []).append(i)
    keys = rowd.keys()
    keys.sort()
    subarrays = [r[rowd[k]] for k in keys]
    for subarray in subarrays:
        subarray.sort(order=sort)
    return zip(keys, subarrays)

def unique_reduce(r, x, reduce):
    elements = np.unique(r[x])
    masks = [r[x]==e for e in elements]
    result = [elements]
    for func in reduce:
        print func
        values = [func(r[m]) for m in masks]
        result.append(values)
    return result
