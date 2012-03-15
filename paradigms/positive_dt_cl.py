from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup

from ._positive_dt_controller_mixin import PositiveDTControllerMixin
from ._positive_dt_paradigm_mixin import PositiveDTParadigmMixin

from experiments.abstract_positive_experiment import AbstractPositiveExperiment
from experiments.abstract_positive_controller import AbstractPositiveController
from experiments.abstract_positive_paradigm import AbstractPositiveParadigm
from experiments.positive_data import PositiveData

from experiments.cl_controller_mixin import CLControllerMixin
from experiments.cl_paradigm_mixin import CLParadigmMixin
from experiments.cl_experiment_mixin import CLExperimentMixin
from experiments.positive_cl_data_mixin import PositiveCLDataMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        AbstractPositiveController, 
        CLControllerMixin,
        PumpControllerMixin,
        PositiveDTControllerMixin,
        ):
    pass

class Paradigm(
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        CLParadigmMixin,
        PositiveDTParadigmMixin,
        ):

    traits_view = View(
            VGroup(
                Include('constant_limits_paradigm_mixin_group'),
                Include('abstract_positive_paradigm_group'),
                Include('pump_paradigm_mixin_syringe_group'),
                label='Paradigm',
                ),
            VGroup(
                Include('speaker_group'),
                Include('dt_group'),
                label='Sound',
                ),
            )

class Data(PositiveData, PositiveCLDataMixin, PumpDataMixin): pass

class Experiment(AbstractPositiveExperiment, CLExperimentMixin):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'PositiveDTCLExperiment'
