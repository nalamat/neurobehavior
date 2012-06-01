'''
Appetitive temporal integration (maximum likelihood method)
-----------------------------------------------------------
:Author: Brad Buran <bburan@alum.mit.edu>
:Method: Adaptive go-nogo (using maximum likelihood)
:Status: Beta.  Has been tested and used on human primates; however, this needs
to be tested on nonhuman subjects to determine efficacy.

Available parameters
....................
fc : Hz
    Center frequency (Hz).  Will be coerced to the nearest frequency for
    which calibration data is available.  Assumes that the frequency of
level : db SPL
    Level of tone
duration : seconds
    Duration of tone (from ramp onset to ramp offset)
rise_fall_time : seconds 
    Rise/fall time of cos^2 envelope 

'''

from traits.api import Instance
from traitsui.api import View, Include, VGroup

from ._positive_dt_controller_mixin import DTControllerMixin
from ._positive_dt_paradigm_mixin import DTParadigmMixin

from experiments.abstract_positive_experiment_v2 import AbstractPositiveExperiment
from experiments.abstract_positive_controller_v2 import AbstractPositiveController
from experiments.abstract_positive_paradigm_v2 import AbstractPositiveParadigm
from experiments.positive_data_v2 import PositiveData

from experiments.ml_controller_mixin import MLControllerMixin
from experiments.ml_paradigm_mixin import MLParadigmMixin
from experiments.ml_experiment_mixin import MLExperimentMixin
from experiments.ml_data_mixin import MLDataMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        DTControllerMixin,
        AbstractPositiveController, 
        MLControllerMixin,
        PumpControllerMixin):
    pass

class Paradigm(
    DTParadigmMixin,
    AbstractPositiveParadigm, 
    PumpParadigmMixin,
    MLParadigmMixin):

    traits_view = View(
        Include('maximum_likelihood_paradigm_mixin_group'),
        VGroup(
            Include('abstract_positive_paradigm_group'),
            Include('pump_paradigm_mixin_syringe_group'),
            label='Paradigm'
        ),
        VGroup(
            Include('dt_group'),
            Include('speaker_group'),
            label='Sound'
        )
    )

class Data(PositiveData, MLDataMixin, PumpDataMixin):
    pass

class Experiment(AbstractPositiveExperiment, MLExperimentMixin):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'PositiveDTCLExperiment'

if __name__ == '__main__':
    import tables
    from os.path import join
    from cns import get_config
    filename = join(get_config('TEMP_ROOT'), 'test_experiment.hd5')
    file = tables.openFile(filename, 'w')
    from experiments.trial_setting import add_parameters
    add_parameters(['test'])
    data = Data(store_node=file.root)
    experiment = Experiment(data=data)
    experiment.configure_traits()
