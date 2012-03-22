Experiment paradigms
====================

Defining an experiment
----------------------

An experiment requires the following classes:

    Data
        An object containing data acquired during an experiment.

        Data is split into two parts, raw and analyzed.  Summary statistics can 
        
        where the experiment data is stored.  This object should contain
        metadata that describes how the data should be stored.  The controller
        will store data it acquires in this object. 

    Controller

        Defines the core logic of the experiment.  The controller is responsible
        for responding to changes in the GUI (e.g. a button press or entry of a
        new value).  For example, when a user clicks on the "start" button to
        begin a new experiment, the controller is responsible for creating a new
        data file, configuring the equipment, and periodically polling the
        equipment and saving new data to the file.

    Paradigm

        The paradigm is simply a container that defines the variables needed by
        the experiment.  For example, appetitive go/nogo paradigm, you would
        need to have variables that define the reward volume and the probability
        of a go trial. 

    Experiment

        Defines the GUI


Using expressions
-----------------

Many parameters defined in the paradigm can be defined as an expression that is
evaluated once per trial.  This allows you to randomize certain parameters, base
their value on the value of another parameter, or adjust the experiment based on
the performance of the subject. 

    * Randomizing the required poke duration for initiating a trial::
      poke_duration = uniform(0.2, 0.4)

    * Set go probability to 0.5, but ensure that no more than five consecutive
      nogos are presented in a row::
      go_probability = 0.5 if c_nogo < 5 else 1.0

    * Set signal offset delay to the duration of the signal::
      signal_offset_delay = duration

    * Randomly select between a 1 kHz tone and a 1 kHz bandwidth noise centered
      at 2 kHz::
      center_frequency = choice([1e3, 2e3])
      bandwidth = 0 if center_frequency == 1e3 else 1e3

    * Present another nogo if the subject false alarmed, otherwise set go
      probability to 0.5 unless there have been 5 nogos in a row::
      go_probability = 0 if fa else (0.5 if c_nogo < 5 else 1)

The expressions can be any Python statement that can be evaluated in a single
line.  All expressions are evaluated in a namespace that contains both Python's
builtin functions along with others deemed useful for behavior experiments.  The
value of each parameter is computed only once when get_current_value is called.
The result is cached.

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

Probability when using a uniform distribution
_____________________________________________

TODO

How the expressions work
------------------------

To compute the value only once per trial, you would do the following steps:

    paradigm.poke_duration = 'uniform(0.2, 0.4)'
    print controller.get_current_value('poke_duration')
    print controller.get_current_value('poke_duration')
    controller.invalidate_current_context()
    print controller.get_current_value('poke_duration')

Both the aversive and appetitive controllers invalidate the cache after each
trial, forcing a recomputation of all expressions.  

    paradigm.poke_duration = 0.5
    controller.invalidate_context()
    print controller.get_current_value('poke_duration')

Why is the poke_duration still set to a random value?  Remember that you must
apply any changes you make to the paradigm before they are reflected in the
actual experiment itself.  When you apply a change, the context cache is
invalidated, so there is no need to call invalidate_current_context as well.

    controller.apply()
    controller.get_current_value('poke_duration')

Before you start the next trial, you must ensure that all remaining expressions
on the stack get evaluated as well.

    controller.evaluate_pending_expressions()

This is handled by the function _apply_context_changes defined in the
AbstractExperimentController.  The function gets called whenever the items in
the current_context dictionary change (e.g. either items get added, removed or
changed). 

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

.. automodule:: paradigms
    :members:

.. automodule:: paradigms.positive_cmr
    :members:

.. automodule:: paradigms.positive_am_noise_cl
    :members:
