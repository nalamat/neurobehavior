The probability of a go/warning trial
=====================================

Early iterations of the Neurobehavior program would select the number of
nogo trials in advance based on a specified criterion (e.g. selecting an
integer from a uniform or exponential distribution.  The user has the advantage
of knowing how many nogo trials will be presented at the beginning of each trial
set.  However, this approach does not mesh well with the idea of reevaluating
the experiment `context` before each trial.  Under the old approach, the number
of nogos is recomputed after every go trial while all other parameters are
recomputed after every trial.  This has the distinct disadvantage of not being
able to adjust the probability of a go/nogo on a trial-by-trial basis.
Furthermore, it masks the subject's experience.

Probability when using a uniform distribution
---------------------------------------------
1/n_trials

