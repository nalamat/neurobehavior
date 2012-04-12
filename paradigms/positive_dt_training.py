from traits.api import Instance
from traitsui.api import View, Include, VGroup

from experiments.positive_stage1_data import PositiveStage1Data
from experiments.positive_stage1_controller import PositiveStage1Controller
from experiments.positive_stage1_experiment import PositiveStage1Experiment
from experiments.positive_stage1_paradigm import PositiveStage1Paradigm

from ._positive_dt_controller_mixin import DTControllerMixin
from ._positive_dt_paradigm_mixin import DTParadigmMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        PositiveStage1Controller,
        PumpControllerMixin,
        DTControllerMixin):

    # Override the set_duration method in TemporalIntegrationControllerMixin
    # which is primarily targeted towards the main appetitive program
    # (positive-behavior-v2) and is expecting a signal_dur_n tag in the circuit.
    # Here, we don't need such a tag.

    def set_duration(self, value):
        self._recompute_time()
        self._recompute_token()
        self._recompute_envelope()

class Paradigm(
        PumpParadigmMixin,
        DTParadigmMixin,
        PositiveStage1Paradigm,
        ):

    traits_view = View(
            VGroup(
                'speaker',
                Include('dt_group'),
                ),
            )

class Data(PositiveStage1Data, PumpDataMixin): pass

class Experiment(PositiveStage1Experiment):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'PositiveDTTraining'
