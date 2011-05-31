import numpy as np

sweetpoint = lambda a, m, k, x: m+(k**-1)*np.log((1+(1+a*a)**0.5)/2.0)
p_yes = lambda a, m, k, x: a + (1-a)*(1+np.exp(-k*(x-m)))**-1

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

    def best_coefficients(self, x, yes=True):
        return self._get_coefficients(self.p(x, yes))

    def best_track_coefficients(self, x, yes=True):
        p = self.p(x, yes)
        self.t_history.append(x)
        self.p_history = np.concatenate((self.p_history, p[np.newaxis]))
        p_track = self.p_history.prod(axis=0)
        return self._get_coefficients(p_track)

    def _get_coefficients(self, p):
        ai, mi, ki = np.unravel_index(p.argmax(), self.shape)
        return self.a[ai, 0, 0], self.m[:, mi, :], self.k[:, :, ki]

    def sweetpoint(self, a, m, k):
        return m+(k**-1)*np.log((1+(1+a*a)**0.5)/2.0)

    def p(self, x, yes=True):
        return self.p_yes(x) if yes else self.p_no(x)

    def p_yes(self, x):
        a, m, k = self.a, self.m, self.k
        return a + (1-a)*(1+np.exp(-k*(x-m)))**-1
        
    def p_no(self, x):
        return 1-self.p_yes(x)

    def p_fa(self, x):
        return self.a

    def send(self, x, yes=True):
        a, m, k = self.best_track_coefficients(x, yes)
        return self.sweetpoint(a, m, k)

class TestCase(object):

    def setUp(self):
        self.track = MF([0.0, 0.2], [-1.0, 3.0, -2.0, 2.0], [0.5])

    def testTrack(self):
        stimuli = [(10, True), (-2, False), (3, True), (3, False)]
        p = [(0.9975, 0.9820, 0.9980, 0.9856)]
