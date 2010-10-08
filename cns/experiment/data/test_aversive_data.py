import unittest
import tables
from os.path import dirname, abspath, join
from cns.data import persistence

from cns.experiment.data.aversive_data import AnalyzedAversiveData
from cns.experiment.data.aversive_data import GrandAnalyzedAversiveData
import numpy as np

from numpy.testing import assert_array_almost_equal
import logging
log = logging.getLogger()
log.setLevel(logging.ERROR)

# only contains remind trials
A = '/Cohort_0/animals/Animal_0/experiments/aversive_date_2010_07_11_08_54_30/Data'
# contains remind, warn and safe trials
B = '/Cohort_0/animals/Animal_0/experiments/aversive_date_2010_07_28_18_20_01/Data'

GA_A = '/Cohort_0/animals/Animal_1/experiments/aversive_date_2010_08_16_15_41_54/Data'
GA_B = '/Cohort_0/animals/Animal_1/experiments/aversive_date_2010_08_18_16_36_51/Data'

PATH = join(abspath(dirname(__file__)), 'test_data.hd5')

class TestAversiveData(unittest.TestCase):

    def setUp(self):
        f = tables.openFile(PATH)
        self.data_a = persistence.load_object(f.getNode(A))
        self.data_b = persistence.load_object(f.getNode(B))

    def testPars(self):
        self.assertEqual(list(self.data_a.pars), [])
        self.assertEqual(list(self.data_b.pars), [50, 55, 60, 65, 70])

    def testWarnParCount(self):
        self.assertEqual(list(self.data_a.par_warn_count), [])
        self.assertEqual(list(self.data_b.par_warn_count), [18, 18, 17, 17, 17])
    def testWarnTrialCount(self):
        self.assertEqual(self.data_a.warn_trial_count, 0)
        self.assertEqual(self.data_b.warn_trial_count, 87)

    def testWarnIndices(self):
        self.assertEqual(list(self.data_a.warn_indices), [])
        warn_indices = [7, 12, 17, 21, 25, 28, 31, 34, 39, 44, 47, 52, 55, 59,
                        64, 68, 72, 77, 80, 85, 89, 92, 97, 100, 104, 108, 111,
                        115, 119, 124, 127, 132, 136, 141, 144, 148, 152, 155,
                        158, 161, 166, 171, 176, 179, 182, 187, 191, 195, 198,
                        203, 206, 209, 214, 217, 220, 223, 228, 233, 236, 240,
                        244, 247, 251, 255, 259, 264, 268, 271, 274, 279, 284,
                        289, 293, 298, 303, 308, 311, 316, 319, 323, 326, 330,
                        333, 338, 341, 346, 351]
        self.assertEqual(list(self.data_b.warn_indices), warn_indices)

class TestAnalyzedAversiveData(unittest.TestCase):

    def setUp(self):
        f = tables.openFile(PATH)
        data = persistence.load_object(f.getNode(A))
        self.data_a = AnalyzedAversiveData(data=data)
        data = persistence.load_object(f.getNode(B))
        self.data_b = AnalyzedAversiveData(data=data)

    def testContactScores(self):
        contact_scores = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.44, 0.36, 1.0, 0.38,
                          0.36, 0.38, 1.0]
        self.assertEqual(list(self.data_a.contact_scores), contact_scores)

        contact_scores = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0,
                          0.16, 0.54, 1.0, 0.0, 0.94, 1.0, 1.0, 1.0, 1.0, 1.0,
                          0.2, 1.0, 1.0, 0.0, 1.0, 1.0, 0.4, 0.0, 1.0, 1.0, 1.0,
                          1.0, 1.0, 0.08, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0,
                          1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0,
                          1.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 1.0,
                          1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0,
                          1.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0,
                          0.82, 0.0, 1.0, 0.54, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0,
                          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0,
                          1.0, 0.78, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0,
                          1.0, 0.68, 1.0, 0.72, 1.0, 0.0, 0.9, 1.0, 1.0, 1.0,
                          1.0, 0.0, 0.54, 0.0, 1.0, 1.0, 0.0, 1.0, 0.04, 1.0,
                          1.0, 1.0, 0.74, 0.0, 1.0, 0.42, 1.0, 1.0, 1.0, 1.0,
                          1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0,
                          1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0,
                          0.88, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.88, 1.0,
                          1.0, 0.0, 0.96, 0.0, 0.0, 0.0, 0.0, 0.98, 1.0, 0.0,
                          1.0, 1.0, 1.0, 1.0, 0.94, 0.42, 1.0, 0.52, 1.0, 0.98,
                          1.0, 1.0, 0.0, 0.8, 1.0, 1.0, 0.0, 1.0, 0.0, 0.66,
                          0.98, 0.92, 1.0, 0.14, 0.0, 0.9, 0.8, 0.0, 0.54, 0.22,
                          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0,
                          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0,
                          1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0,
                          0.0, 1.0, 0.0, 0.0, 1.0, 0.74, 0.0, 0.0, 0.0, 0.74,
                          0.0, 1.0, 0.76, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 1.0,
                          0.0, 1.0, 1.0, 0.38, 1.0, 1.0, 1.0, 1.0, 0.82, 1.0,
                          1.0, 1.0, 1.0, 0.0, 0.08, 0.14, 1.0, 1.0, 0.0, 1.0,
                          1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
                          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0,
                          0.56, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.06, 0.0,
                          0.78, 0.0, 0.0, 0.0, 1.0, 0.74, 1.0, 1.0, 1.0, 1.0,
                          1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
                          1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.assertEqual(list(self.data_b.contact_scores), contact_scores)

    def testParInfo(self):
        #            PAR S   W   FA  H   HF     FAF    D_NG    D_G
        par_info = [[50, 55, 18, 9,  17, 0.944, 0.163, 2.572,  2.434],
                    [55, 55, 18, 13, 11, 0.611, 0.236, 1.000,  1.123],
                    [60, 56, 17, 10, 9,  0.529, 0.178, 0.994,  0.915],
                    [65, 46, 17, 7,  8,  0.470, 0.152, 0.953,  0.767],
                    [70, 53, 17, 14, 3,  0.176, 0.264, -0.298, -0.087]] 
        assert_array_almost_equal(self.data_b.par_info, par_info, 3)

class TestGrandAnalyzedAversiveData(unittest.TestCase):

    def setUp(self):
        f = tables.openFile(PATH)

        data = persistence.load_object(f.getNode(A))
        data_a = AnalyzedAversiveData(data=data)
        data = persistence.load_object(f.getNode(B))
        data_b = AnalyzedAversiveData(data=data)
        self.ga_a = GrandAnalyzedAversiveData(data=[data_a, data_b])

        data = persistence.load_object(f.getNode(GA_A))
        data_a = AnalyzedAversiveData(data=data)
        data = persistence.load_object(f.getNode(GA_B))
        data_b = AnalyzedAversiveData(data=data)
        self.ga_b = GrandAnalyzedAversiveData(data=[data_a, data_b])

    def testParInfo(self):
        #            PAR    S    W   FA  H   HF     FAF    D_NG   D_G
        par_info = [[50, 55, 18, 9,  17, 0.944, 0.163, 2.572,  2.434],
                    [55, 55, 18, 13, 11, 0.611, 0.236, 1.000,  1.123],
                    [60, 56, 17, 10, 9,  0.529, 0.178, 0.994,  0.915],
                    [65, 46, 17, 7,  8,  0.470, 0.152, 0.953,  0.767],
                    [70, 53, 17, 14, 3,  0.176, 0.264, -0.298, -0.087]] 
        assert_array_almost_equal(self.ga_a.par_info, par_info, 3)

        #            PAR    S    W   FA  H   HF     FAF    D_NG   D_G
        par_info = [[0.032, 120, 38, 14, 12, 0.316, 0.117, 0.712, 0.678],
                    [0.064, 122, 39, 15, 12, 0.308, 0.123, 0.658, 0.655],
                    [0.128, 111, 40, 11, 16, 0.400, 0.099, 1.033, 0.904],
                    [0.256, 122, 40, 15, 22, 0.550, 0.123, 1.286, 1.283],
                    [0.512, 124, 40, 19, 31, 0.775, 0.153, 1.778, 1.913]]
        assert_array_almost_equal(self.ga_b.par_info, par_info, 3)

def test_analyzed_aversive_view():
    from cns.experiment.data.aversive_data_view import AnalyzedAversiveDataView
    f = tables.openFile(PATH)
    data = persistence.load_object(f.getNode(B))
    analyzed = AnalyzedAversiveData(data=data)
    print analyzed.warn_trial_count
    view = AnalyzedAversiveDataView(analyzed=analyzed)
    view.configure_traits()

if __name__ == '__main__':
    unittest.main()
    #test_analyzed_aversive_view()
