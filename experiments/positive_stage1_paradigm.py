from abstract_experiment_paradigm import AbstractExperimentParadigm
from .evaluate import Expression

class PositiveStage1Paradigm(AbstractExperimentParadigm):

    speaker = Expression("'primary'", label='Output speaker', context=True,
            log=True)
