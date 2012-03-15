from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup

from experiments.positive_stage1_data import PositiveStage1Data
from experiments.positive_stage1_controller import PositiveStage1Controller
from experiments.positive_stage1_experiment import PositiveStage1Experiment
from experiments.abstract_experiment_paradigm import AbstractExperimentParadigm

from ._positive_am_noise_controller_mixin import PositiveAMNoiseControllerMixin
from ._positive_am_noise_paradigm_mixin import PositiveAMNoiseParadigmMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        PositiveStage1Controller,
        PumpControllerMixin,
        PositiveAMNoiseControllerMixin):

    # Override the set_duration method in which is primarily targeted towards
    # the main appetitive program (positive-behavior-v2 and
    # positive-behavior-v3) and is expecting a signal_dur_n tag in the circuit.
    # Here, we don't need such a tag.

    def set_duration(self, value):
        self._recompute_time()
        self._recompute_noise_token()
        self._recompute_sam_envelope()
        self._recompute_cos_envelope()
        self.iface_behavior.cset_tag('signal_dur_n', value, 's', 'n')

class Paradigm(
        AbstractExperimentParadigm, 
        PumpParadigmMixin,
        PositiveAMNoiseParadigmMixin,
        ):

    traits_view = View(
            VGroup(
                Include('pump_paradigm_mixin_syringe_group'),
                label='Paradigm',
                ),
            VGroup(
                Include('signal_group'),
                label='Sound',
                ),
            )

class Data(PositiveStage1Data, PumpDataMixin): pass

class Experiment(PositiveStage1Experiment):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'AMNoiseTraining'

