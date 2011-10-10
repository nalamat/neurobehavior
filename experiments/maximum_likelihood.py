import numpy as np

def sweetpoint(a, m, k):
    '''
    Compute point of minimum variance when estimating sigmoid
    a (false alarm rate), m (midpoint of function) and k (slope)
    '''
    return m+(k**-1)*np.log((1+(1+a*a)**0.5)/2.0)

p_yes = lambda a, m, k, x: a + (1-a)*(1+np.exp(-k*(x-m)))**-1
p_no = lambda a, m, k, x: 1-p_yes(a, m, k, x)

# Given p, return x
x = lambda a, m, k, p: (np.log((1-a)/(p-a)-1)/-k)+m

def sweetpoint_yes_probability():
    alpha = arange(0, 1, .01)
    z = (1+8*alpha)**0.5
    p = (2*alpha+1+z)/(3+z)
    plot(alpha, p)
    xlabel('FA rate')
    ylabel('Probability of YES response at sweetpoint') 
    show()

class MaximumLikelihood(object):

    def __init__(self, a, m, k):
        '''
        a
            alpha, the false alarm rate
        m
            midpoint of the function
        k
            slope of the function
        '''
        sa = len(a)
        sm = len(m)
        sk = len(k)
        self.shape = sa, sm, sk
        self.a = np.array(a)[:, np.newaxis, np.newaxis]
        self.m = np.array(m)[np.newaxis, :, np.newaxis]
        self.k = np.array(k)[np.newaxis, np.newaxis, :]
        self.p_history = np.array([]).reshape((-1, sa, sm, sk))
        self.t_history = []
        self.r_history = []

    def update_estimate(self, x, yes):
        p = self.p(x, yes)
        self.t_history.append(x)
        self.r_history.append(yes)
        self.p_history = np.concatenate((self.p_history, p[np.newaxis]))
        
    def best_coefficients(self):
        p = self.p_history.prod(axis=0)
        ai, mi, ki = np.unravel_index(p.argmax(), self.shape)
        return self.a[ai, 0, 0], self.m[0, mi, 0], self.k[0, 0, ki]

    def sweetpoint(self, a, m, k):
        return sweetpoint(a, m, k)

    def p(self, x, yes=True):
        args = self.a, self.m, self.k, x
        return p_yes(*args) if yes else p_no(*args)
    
    def x(self, a, m, k, p):
        return x(a, m, k, p)

class TestCase(object):

    def setUp(self):
        self.track = MF([0.0, 0.2], [-1.0, 3.0, -2.0, 2.0], [0.5])

    def testTrack(self):
        stimuli = [(10, True), (-2, False), (3, True), (3, False)]
        p = [(0.9975, 0.9820, 0.9980, 0.9856)]
