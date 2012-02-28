from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup

from experiments.positive_stage1_data import PositiveStage1Data
from experiments.positive_stage1_controller import PositiveStage1Controller
from experiments.positive_stage1_experiment import PositiveStage1Experiment
from experiments.abstract_experiment_paradigm import AbstractExperimentParadigm

from ._positive_dt_controller_mixin import PositiveDTControllerMixin
from ._positive_dt_paradigm_mixin import PositiveDTParadigmMixin

from experiments import PumpControllerMixin, PumpParadigmMixin

class Controller(
        PositiveStage1Controller,
        PumpControllerMixin,
        PositiveDTControllerMixin):

    # Override the set_duration method in TemporalIntegrationControllerMixin
    # which is primarily targeted towards the main appetitive program
    # (positive-behavior-v2) and is expecting a signal_dur_n tag in the circuit.
    # Here, we don't need such a tag.

    def set_duration(self, value):
        self._recompute_time()
        self._recompute_token()
        self._recompute_envelope()

class Paradigm(
        AbstractExperimentParadigm, 
        PumpParadigmMixin,
        PositiveDTParadigmMixin,
        ):

    traits_view = View(
            VGroup(
                Include('pump_paradigm_mixin_syringe_group'),
                label='Paradigm',
                ),
            VGroup(
                Include('temporal_integration_group'),
                label='Sound',
                ),
            )

class Data(PositiveStage1Data): pass

class Experiment(PositiveStage1Experiment):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'PositiveDTTraining'
