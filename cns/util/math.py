'''
Collection of math-related functions to assist in various computations.
'''
from __future__ import division
import numpy as np
from scipy.stats import norm

def d_prime(safe, warn, fa, hit, clip=0.01):
    '''Computes d' given number of safes, warns, false alarms and hits.
    Primarily a utility function for scripting.

    This implements the algorithm described in Macmillan & Creelman (2004,
    p.21), particularly for edge cases where observed hits and/or misses are
    zero. This assumes a go-nogo paradigm.
    
    Parameters
    ==========
    safe
        Number of safe (noise) trials
    warn
        Number of warn (signal) trials
    fa
        Number of false alarms ("YES" responses to noise trials)
    hit
        Number of hits ("YES" responses to signal trials)
    clip
        Ensure that the false alarm and hit fractions to the range [clip,
        1-clip].  This is important for "perfect" experiments (which can occur
        if the trial count is low enough) since this generates an infinite
        z-score.  Note that the default value of 0.01 for clip means that d'
        is restricted to the range betwen -4.65 and 4.65.  This is an OK default
        since most people are interested in where d' is close to 1.

    Returns
    =======
    Tuple (d', C)
    
    d'
        Discriminability index
    C
        Criterion used by the observer

    >>> d_prime(80, 80, 5, 67)
    2.518
    >>> d_prime(50, 20, 5, 15)
    1.956
    >>> d_prime(10, 10, 0, 10, 0.01)
    4.653
    >>> d_prime(10, 10, 0, 10, 0.05)
    3.290
    '''

    fa_frac = np.clip(fa/safe, clip, 1-clip)
    hit_frac = np.clip(hit/warn, clip, 1-clip)
    z_hit = norm.ppf(hit_frac)
    z_fa = norm.ppf(fa_frac)
    d = z_hit-z_fa
    c = (z_hit+z_fa)/2
    return d


def nextpow2(i):
    '''Returns the nearest number >= i that is a power of 2
    '''
    n = 2
    while n<i: n=n*2
    return n

def gcd(a, b):
    '''Returns greatest common denominator of a and b
    '''
    while b: a, b = b, a%b
    return a

def lcm(a, b):
    '''Returns least common multiple of a and b
    '''
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
