import settings
import sys
from os.path import join

def test_experiment():
    # Since we are testing our experiment paradigm, we need to provide a
    # temporary HDF5 file (i.e. a "dummy" cohort file) that the experiment can
    # save its data to.
    import tables
    from cns import TEMP_ROOT
    from experiments.positive_am_noise_experiment import PositiveAMNoiseExperiment

    file_name = join(TEMP_ROOT, 'test.h5')
    test_file = tables.openFile(file_name, 'w')

    experiment = PositiveAMNoiseExperiment(store_node=test_file.root)
    experiment.edit_traits(kind='live', view='physiology_view')
    experiment.edit_traits(kind='livemodal')

def profile_experiment():
    from cns import TEMP_ROOT
    import cProfile
    profile_data_file = join(TEMP_ROOT, 'profile.dmp')
    cProfile.run('test_experiment()', profile_data_file)
    import pstats
    p = pstats.Stats(profile_data_file)
    p.strip_dirs().sort_stats('cumulative').print_stats(50)

if __name__ == '__main__':
    profile_experiment()
