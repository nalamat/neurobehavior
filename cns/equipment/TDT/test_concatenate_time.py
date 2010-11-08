from timeit import timeit
import numpy as np
from numpy import arange, c_, r_

#x = np.arange(64)
ch = 4
comp = 2
step = ch*comp

reshape = lambda x, i, n: x.reshape((-1,comp))[i::n].ravel()

#setup = 'from __main__ import method1, method2, method3, method4, method5'
setup = 'from __main__ import method1, method2, method5'

'AABBCCDDAABBCCDD'
'0123456701234567'

'A A B B C C D D A A B  B   C   C   D   D '
'0 1 2 3 4 5 6 7 8 9 10 11  12  13  14  15'

def method1():
    return c_[[reshape(x, i, ch) for i in range(ch)]]

def method2():
    data = []
    for i in range(0, step, comp):
        temp = []
        for j in range(comp):
            temp.append(x[i+j::step])
        data.append(c_[temp])
    return r_[data].reshape((-1,ch))

#def method3():
#    size = len(x)
#    for i in range(0, step, comp):
#        for j in range(comp):
#            
#
#    indices = [c_[arange(i, size, step), arange(i+1, size, step)].ravel() \
#            for i in range(0, step, 2)]
#    indices = np.r_[indices]
#    return x[indices]
#
#def method4():
#    size = len(x)
#    indices = [arange(i, size, step) for i in range(0, step, 2)]
#    indices = r_[[c_[i, i+1].ravel() for i in indices]]
#    return x[indices]

def method5():
    t = np.empty((len(x)/ch, ch))
    for i in range(ch):
        for j in range(comp):
            t[j::comp,i] = x[i*comp+j::step]
        #t[ ::2,i] = x[i::step]
        #t[1::2,i] = x[i::step]
    return t

if __name__ == '__main__':
    x = np.arange(64)
    #print 'Shapes agree ', method1().shape==method2().shape==method3().shape
    print 'Shapes agree ', method1().shape==method2().shape
    print 'Values agree (1,2)', (method1()==method2()).all() 
    #print 'Values agree (1,3)', (method1()==method3()).all()
    #print 'Values agree (1,4)', (method1()==method4()).all()
    print 'Values agree (1,5)', (method1()==method5()).all()

    #print method1()
    #print method2()

    x = np.arange(800)
    print 'Samples are low (800)'
    print 'Method 1 ', timeit('method1()', setup, number=1000)
    print 'Method 2 ', timeit('method2()', setup, number=1000)
    #print 'Method 3 ', timeit('method3()', setup, number=1000)
    #print 'Method 4 ', timeit('method4()', setup, number=1000)
    print 'Method 5 ', timeit('method5()', setup, number=1000)

    x = np.arange(800000)
    print 'Samples are high (800000)'
    print 'Method 1 ', timeit('method1()', setup, number=100)
    print 'Method 2 ', timeit('method2()', setup, number=100)
    #print 'Method 3 ', timeit('method3()', setup, number=100)
    #print 'Method 4 ', timeit('method4()', setup, number=100)
    print 'Method 5 ', timeit('method5()', setup, number=100)
