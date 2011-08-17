.. toctree::
    :maxdepth: 2

Defining an experiment
======================

An experiment requires the following pieces:

    Data
        An object containing data acquired during an experiment.

        Data is split into two parts, raw and analyzed.  Summary statistics can 
        
        where the experiment data is stored.  This object should
        contain metadata that describes how the data should be stored.  The
        controller will store data it acquires in this object.  At the end of an
        experiment, the stored data will be persisted to a file via the
        `cns.data.persistence` class.

    Controller

        Defines the core logic of the experiment.  The controller is responsible
        for responding to changes in the GUI (e.g. a button press or entry of a
        new value).  For example, when a user clicks on the "start" button to
        begin a new experiment, the controller is responsible for creating a new
        data file, configuring the equipment, and periodically polling the
        equipment and saving new data to the file.

    Paradigm
        <todo>
    GUI
        These are classes that define how the user interface looks


Experiments consist of several key components

* Paradigm
* Controller
* Experiment
* Data

The paradigm is simply a container for variables needed by the experiment.  If you were running an appetitive go/nogo paradigm, you would need to know the reward volume and the probability of a go trial. 

Using expressions
-----------------

Many parameters accept an expression that is evaluated once per trial.  This allows you to randomize certain parameters, base their value on the value of another parameter, or adjust the experiment based on the performance of the subject. 

* Randomizing the required poke duration for initiating a trial
poke_duration = uniform(0.2, 0.4)

* Set go probability to 0.5, but ensure that no more than five consecutive nogos are presented in a row
go_probability = 0.5 if c_nogo < 5 else 1.0

* Set signal offset delay to the duration of the signal
signal_offset_delay = duration

* Randomly select between a 1 kHz tone and a 1 kHz bandwidth noise centered at 2 kHz
center_frequency = choice([1e3, 2e3])
bandwidth = 0 if center_frequency == 1e3 else 1e3

* Present another nogo if the subject false alarmed, otherwise set go probability to 0.5 unless there have been 5 nogos in a row
go_probability = 0 if fa else (0.5 if c_nogo < 5 else 1)

The expressions can be any Python statement that can be evaluated in a single line.  All expressions are evaluated in a namespace that contains both Python's builtin functions along with others deemed useful for behavior experiments.  The value of each parameter is computed only once when get_current_value is called.  The result is cached.

To compute the value only once per trial, you would do the following steps:

>>> paradigm.poke_duration = 'uniform(0.2, 0.4)'
>>> print controller.get_current_value('poke_duration')
>>> print controller.get_current_value('poke_duration')
>>> controller.invalidate_current_context()
>>> print controller.get_current_value('poke_duration')

Both the aversive and appetitive controllers invalidate the cache after each trial, forcing a recomputation of all expressions.  

>>> paradigm.poke_duration = 0.5
>>> controller.invalidate_current_context()
>>> print controller.get_current_value('poke_duration')

Why is the poke_duration still set to a random value?  Remember that you must apply any changes you make to the paradigm before they are reflected in the actual experiment itself.  When you apply a change, the context cache is invalidated, so there is no need to call invalidate_current_context as well.

>>> controller.apply()
>>> controller.get_current_value('poke_duration')

Before you start the next trial, you must ensure that all remaining expressions on the stack get evaluated as well.

>>> controller.evaluate_pending_expressions()

Note that any time the value of a context variable changes, the controller looks for a method called set_variable_name.  This ensures that all changes are relayed to other parts of the program, the hardware (e.g. the DSP microcode) or the pump.  How does this work?

init_experiment - Initializes the hardware
start_experiment
evaluate_pending_expressions

Since the prior value of all context variables is None when evaluate_pending_expressions is called for the first time, all the requisite set_<parameter> methods will be called with the initial value of the parameter.

trigger_next

Upload the necessary signal to the audio buffers

monitor_behavior

Poll the DSP continuously to determine when a trial has completed.

invalidate_current_context
get_next_parameter
trigger_next




The apply/revert handler
------------------------



