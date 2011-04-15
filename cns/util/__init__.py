def to_list(string):
    '''
    Converts a string to a list of integers

    >>> to_list('11')
    [11]

    >>> to_list('1-4')
    [1, 2, 3, 4]

    >>> to_list('1, 3-6')
    [1, 3, 4, 5, 6]

    >>> to_list('1, 3-4, 10')
    [1, 3, 4, 10]

    >>> to_list('1, 3 - 4, 10')
    [1, 3, 4, 10]
    '''
    elements = [s.strip() for s in string.split(',')]
    indices = []
    for element in elements:
        if '-' in element:
            lb, ub = [int(e.strip()) for e in element.split('-')]
            indices.extend(range(lb, ub+1))
        elif element == '':
            pass
        else:
            indices.append(int(element))
    return indices

