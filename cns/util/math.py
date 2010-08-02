def nextpow2(i):
    n = 2
    while n<i: n=n*2
    return n

def gcd(a, b):
    while b: a, b = b, a%b
    return a

def lcm(a, b):
    return a*b/gcd(a, b)

def ensure_monotonic(x, idx):
    raise NotImplementedError('there is a bug here')
    for i in range(idx, len(x)):
        if x[i]<x[i-1]:
            x[i] = x[i-1]
    for i in range(idx, 0, -1):
        if x[i-1]>x[i]:
            x[i-1] = x[i]
    return x
