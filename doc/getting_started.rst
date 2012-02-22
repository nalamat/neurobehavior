===============
Getting Started
===============

Organization of the code
========================
The code is structured into several folders:

    cns.channel
            TODO
    experiment
        signal
    scripts
        Typically short scripts for processing and analyzing data.  The main
        difference between scrips and apps is that scripts typically are not
        interactive.
    launchers
        Demo scripts that I wrote to test the functionality of various features
        of the program.  Many of these scripts are currently broken since I
        don't maintain them well.

cns library
-----------
    experiments.data
        Objects that handle storing and analyzing experimental data.  Objects
        are typically split into RawData and AnalyzedData.
    experiments.controller
        Objects that manage the equipment equipment, responding to user input and 
