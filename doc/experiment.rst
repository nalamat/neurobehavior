.. toctree::
    :maxdepth: 2

Defining an experiment
======================

We need several pieces to define an experiment:

    Data
        An object where the experiment data is stored.  This object should
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

