from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VGroup

from ._positive_dt_controller_mixin import PositiveDTControllerMixin
from ._positive_dt_paradigm_mixin import PositiveDTParadigmMixin

from experiments import (
        # Controller and mixins
        AbstractPositiveController,
        ConstantLimitsControllerMixin, 
        PumpControllerMixin,

        # Paradigm and mixins
        AbstractPositiveParadigm,
        ConstantLimitsParadigmMixin,
        PumpParadigmMixin,

        # The experiment
        AbstractPositiveExperiment,
        ConstantLimitsExperimentMixin,

        # Data
        PositiveData,
        PositiveConstantLimitsDataMixin
        )

class Controller(
        AbstractPositiveController, 
        ConstantLimitsControllerMixin,
        PumpControllerMixin,
        PositiveDTControllerMixin,
        ):
    pass

class Paradigm(
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        ConstantLimitsParadigmMixin,
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

class Data(PositiveData, PositiveConstantLimitsDataMixin): pass

class Experiment(AbstractPositiveExperiment, ConstantLimitsExperimentMixin):

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'PositiveDTCLExperiment'
