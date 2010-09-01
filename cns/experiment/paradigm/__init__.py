'''
Experiment Paradigms
====================

Experiment paradigms contain all the parameters that define the structure and
logic of the experiment (and the associated FPGA circuit that needs to be
loaded).  For example, when you run an aversive experiment you need to define
what the target signal is and when the punishment is activated (relative to the
target onset).  In most cases, the paradigm *does not* define parameters
relevant to data analysis.  In a paradigm where the animal is trained to

There are exceptions to this rule.  If you are running a 2AFC paradigm, the
paradigm needs a score so it can compute the next step in the staircase.  The
easiest way to determine if the paradigm is 
you must incorporate some scoring algorithm (and it's parameters) into your
paradigm.

When determining whether the animal responded
correctly to a trial, you typically need to
you need to determine
a hit or miss, you need to 

A paradigm is an object that provides a place where you can define all of these
parameters.

the
punishment is presented (e.g. how long does the animal have to respond once the
target is presented?)it be presented immediately after the
target)
often the
target (the conditioned stimulus) is presented 
sequence that defines how  a target that
the animal must listen for.
The "safe" (or intertrial) signal indicates that i


experiment.  


experiment.   that the user must configure prior
to starting the experiment.  
