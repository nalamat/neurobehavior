def dec2bin(n):
    """
    A simple look-up method of getting binary string from an integer designed
    for efficiency.
    """
    hexDict = { '0':'0000', '1':'0001', '2':'0010', '3':'0011', '4':'0100',
            '5':'0101', '6':'0110', '7':'0111', '8':'1000', '9':'1001',
            'a':'1010', 'b':'1011', 'c':'1100', 'd':'1101', 'e':'1110',
            'f':'1111', 'L':''}

    # create hex of int, remove '0x'. now for each hex char,
    # look up binary string, append in list and join at the end.
    return ''.join([hexDict[hstr] for hstr in hex(n)[2:]])

# Python 2.6 has a builtin binary function that is much faster than the dec2bin
# implementation above, so we check to see if our version of Python supports it.
# If not (i.e. we're running Python version <= 2.5), we assign bin as an alias
# for dec2bin.
try: bin(0)
except NameError: 
    bin = dec2bin
