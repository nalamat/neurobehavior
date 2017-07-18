Experiment paradigms
====================

The framework that these paradigms are built on allow the user to::

    * Rove almost any of the variables specified in the paradigm

    * Rove multiple variables

    * Specify expressions for most of the variables.  These expressions can use
      the value of other variables.

    * Change the value of any variable during an experiment.

This allows you to create a single paradigm that can handle a variety of tasks
quite easily.  For example, the `positive_dt_cl` paradigm is being used to ask
several questions::

    * By roving `level` for 50 trials at a time before switching to a new tone
      duration, one can explore the subject's temporal integration window.

    * In roving `duration` and `level`, a certain duration and level pair can be
      made more frequent.

    * By modifying the `go_probability` expression on a session-by-session
      basis, one can ask whether the frequency of go trials influences the
      subject's criterion.

Before you start to write a new experiment, you should ask whether one of the
existing experiments will serve your needs.  It may be as simple as roving
certain parameters in lockstep or using an expression for a certain value.

It may be as simple as adding a new variable to the experiment.  If this new
variable can be added while maintaining backwards-compatibility, you can modify
the existing experiment.  Otherwise, simply make a copy of the relevant files.

Defining an experiment
----------------------

An experiment is defined by three main classes, the `Controller`, `Experiment`
and `Paradigm`.  For historical reasons the experiment class is also a container
for an additional class, the `Data` class.  

    Controller

        Defines the core logic of the experiment and is responsible for::
            1. Configuring and controlling the hardware (e.g. water pump, DSP
               devices, attenuators)
            2. Responding to user input via the GUI (e.g. button presses or
               entry of a new value in a widget)
        For example, when a user clicks on the "start" button to begin a new
        experiment, the controller is responsible for creating a new data file,
        configuring the equipment, and periodically polling the equipment and
        saving new data to the file.

    Paradigm

        The paradigm is a container that defines the variables needed by the
        experiment (e.g. an appetitive go/nogo paradigm would have variables
        that define the reward volume and the probability of a go trial).

    Data

        An object containing data acquired during an experiment.

    Experiment

        Creates the GUI plots and lays out the GUI

Using expressions
-----------------

Many parameters defined in the paradigm can be defined as an expression that is
evaluated once per trial.  This allows you to randomize certain parameters, base
their value on the value of another parameter, or adjust the experiment based on
the performance of the subject. 

    * Randomizing the required poke duration for initiating a trial::

        poke_duration = 'uniform(0.2, 0.4)'

    * Set go probability to 0.5, but ensure that no more than five consecutive
      nogos are presented in a row::

        go_probability = '0.5 if c_nogo < 5 else 1.0'

    * Set signal offset delay to the duration of the signal::

        signal_offset_delay = 'duration'

    * Randomly select between a 1 kHz tone and a 1 kHz bandwidth noise centered
      at 2 kHz::

          center_frequency = 'choice([1e3, 2e3])'
          bandwidth = '0 if center_frequency == 1e3 else 1e3'

    * Present another nogo if the subject false alarmed, otherwise set go
      probability to 0.5 unless there have been 5 nogos in a row::

        go_probability = '0 if fa else (0.5 if c_nogo < 5 else 1)'

The expressions can be any Python statement that can be evaluated in a single
line.  All expressions are evaluated in a namespace that contains both Python's
builtin functions along with others deemed useful for behavior experiments.  The
value of each parameter is computed only once when get_current_value is called.
The result is cached.

Available expressions
.....................

.. autoclass:: experiments.evaluate.ParameterExpression

Handling GO/WARN probability
............................

A great example is how we handle the probability of a go or warning trial being
presented.  Early iterations of the Neurobehavior program would select the
number of nogo (i.e. safe) trials in advance based on a specified criterion
(e.g. selecting an integer from a uniform or exponential distribution.  The user
has the advantage of knowing how many nogo trials will be presented at the
beginning of each trial set.  However, this approach does not mesh well with the
idea of reevaluating the experiment context before each trial.  Under the old
approach, the number of nogos is recomputed after every go trial while all other
parameters are recomputed after every trial.  This has the distinct disadvantage
of not being able to adjust the probability of a go/nogo on a trial-by-trial
basis.  Furthermore, it does not make it clear (to the experimenter) how
predictable it will be that the next trial is a go trial.

The :func:`evaluate.h_uniform` function can be used to emulate the approach used
in early iterations of Neurobehavior in which a decision about the number of
trials (e.g. safe trials) is determined at the beginning of a block.  When
number of trials is estimated from a uniform distribution, this creates a skewed
probability.  That is, as the number of safe trials increases, the likelihood
that the next trial is a warn also increases.  The probability of the next trial
being a warn is known as the hazard probability.  By using the hazard function
of the uniform distribution, we can emulate this decision metric by computing
the hazard probability given the number of consecutive safe/nogo trials and the
desired range of nogo/safe trials.  For example, if we want at least 3 but not
more than 5 nogo trials, then there's only three slots in which the go trial can
occur (the fourth, fifth or sixth slot).  Given three nogo trials, the subject
knows that the probability of a go trial occuring on the fourth slot is 1/3.  If
there have been four nogo trials, then the subject knows the probability of the
fifth trial being a go is 1/2 (because there are only two slots remaining).  If
there have been five nogo trials, the subject knows the next trial must be a
warn.

Available expressions
.....................

.. automodule:: experiments.evaluate

How the expressions work
........................

To compute the value only once per trial, you would do the following steps::

    >>> paradigm.poke_duration = 'uniform(0.2, 0.4)'
    >>> print controller.get_current_value('poke_duration')
    0.321
    >>> print controller.get_current_value('poke_duration')
    0.321
    >>> controller.refresh_context()
    >>> print controller.get_current_value('poke_duration')
    0.462

Both the aversive and appetitive controllers invalidate the cache after each
trial, forcing a recomputation of all expressions::

    >>> paradigm.poke_duration = 0.5
    >>> controller.refresh_context()
    >>> print controller.get_current_value('poke_duration')
    0.743

Why is the poke_duration still set to a random value?  Remember that you must
apply any changes you make to the paradigm before they are reflected in the
actual experiment itself.  When you apply a change, the context cache is
invalidated, so there is no need to call invalidate_current_context as well::

    >>> controller.apply()
    >>> controller.get_current_value('poke_duration')
    0.5

Before you start the next trial, you must ensure that all remaining expressions
on the stack get evaluated as well::

    controller.evaluate_pending_expressions()

This is handled by :func:`AbstractExperimentController._apply_context_changes`.
The function gets called whenever the items in current_context change (e.g.
either items get added, removed or changed). 

When you call :func:`AbstractExperimentcontroller.invalidate_context`, this sets
current_context to an empty dictionary (e.g. the values are no longer valid
because they reflect the old trial and need to be recomputed).  When you call
:func:`AbstractExperimentController.evaluate_pending_expressions`, the new value
of each parameter is computed and added to current_context.  As the values are
added to current_context,
:func:`AbstractExperimentController._apply_context_changes` is called for each
addition and it checks to see if the value has changed since the last trial.  If
so, it calls `Controller.set_parameter_name` function with the new value.

.. note::
    
    If the value of a parameter is an expression, it will get recomputed before
    each trial.  However, if the result of the expression is the same as the
    prior trial, `Controller.set_parameter_name` will not be called.

Note that on the very first call to
`AbstractExperimentController.get_current_value` and
`AbstractExperimentController.evaluate_pending_expressions`, the prior value of
all context variables is None.  Therefore, the `Controller.set_parameter_name`
is called for every parameter defined in the paradigm.

The apply/revert handler
------------------------

TODO

Available Paradigms
===================

.. automodule:: paradigms.positive_cmr

.. automodule:: paradigms.positive_am_noise_cl

.. automodule:: paradigms.positive_dt_cl

.. automodule:: paradigms.positive_dt_ml

Known bugs with the experiment paradigms
========================================

* When the same epoch is stored in all_poke_epoch and poke_epoch, the start/end
  timestamps differ by a couple of cycles.  This number varies from epoch to
  epoch.

* Sometimes we get trials that aren't properly saved to the trial log file.
  This is a rare occurance (once every blue moon) and is related to an
  IndexError that you will see.

* Sometimes triggering a remind in the appetitive paradigm will result in the
  prior trial being logged incorrectly.

* Sometimes the `trigger_next()` method on the experiment controller fails to
  fire (this appears to occur once in a while when you request a remind.  If
  this happens you can manually force a trigger by going to the Python shell and
  typing `controller.trigger_next()`.

* Python's pickle module is used to save and load the Paradigm and
  PhysiologySettings objects.  This module is a bit finicky (if you rename your
  experiment paradigms, etc, this may break the ability to load your saved
  settings.

