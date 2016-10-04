Python scripts and applications
===============================

Running experiments
-------------------

Edit cohort (edit_cohort.py)
............................

Create a cohort file for running behavior experiments.  Editing the file
manually or via edit_cohort.py after it has been created is *not recommended*.

Load experiment (load_experiment.py)
....................................

For information on how to use this script, pass the -h flag to the command::

    c:\\> load_experiment.py -h

Which will give you the following message::

    usage: load_experiment.py [-h] [-r ROVE [ROVE ...]] [-a ANALYZE [ANALYZE ...]]
                              [--repeats] [--debug]
                              [-p | --memory | -t | -i | -f FILE] [-n]
                              [--address ADDRESS] [--save-microphone]
                              [--cal CAL CAL | --att] [--equalized]
                              [--modify-path]
                              type

    Launch experiment

    positional arguments:
      type                  The type of experiment to launch

    optional arguments:
      -h, --help            show this help message and exit
      -r ROVE [ROVE ...], --rove ROVE [ROVE ...]
                            Parameter(s) to rove
      -a ANALYZE [ANALYZE ...], --analyze ANALYZE [ANALYZE ...]
                            Parameter(s) to analyze
      --repeats             Specify number of repeats for each trial setting
      --debug               Prevents some exceptions from being silenced
      -p, --profile         Profile experiment
      --memory              Graph memory usage
      -t, --test            Test experiment
      -i, --inspect         Print available parameters
      -f FILE, --file FILE  File to save data to
      -n, --neural          Acquire neurophysiology
      --address ADDRESS     TDT RPC server address (in the format hostname:port).
                            For example, localhost:3333 or
                            regina.cns.nyu.edu:3333.
      --save-microphone     Save microphone data?
      --cal CAL CAL         Calibration files to use for primary and secondary
                            speaker
      --att                 Treat signal level as an attenuation value
      --equalized           Use equalized calibration?
      --modify-path         Although virtualenv is recommended as the best tool
                            for managing stable and developmental verisons of
                            Neurobehavior on a single computer, programmers coming
                            from Matlab tend to prefer the approach of creating a
                            copy of the program to a new folder each time and
                            having the program update the system path based on its
                            current directory. This option is not throughly
                            tested. Use at your own risk.

Analyzing data
--------------

.. note::

    Some of the analysis operations designed to work with the raw physiology
    data (e.g.  decimating the waveform, computing the RMS or extracting spikes)
    typically operate on the data in segments as the raw data is too large to
    fit in computer memory.  The size of the segment is defined by CHUNK_SIZE
    (in cns.settings).  If you are getting memory errors, set CHUNK_SIZE to a
    smaller value.  

    See `overriding defaults defined in cns.settings` for detail on how to
    override this value on a per-user or per-computer basis.

    In general, you should not encounter memory issues unless there are extended
    periods of artifacts in your neural data.  Such artifacts typically occur
    when the wireless headstage falls off or is moved further away from the base
    station.  Since this usually occurs only at the beginning or end of an
    experiment, use the truncate waveform and zero waveform options in the
    review physiology program.

Create missing timeseries data (create_missing_time_data.py)
............................................................

The earliest appetitive physiology experiments (up until ~ the first week of
September, 2011) contain only TTL data sampled at a low resolution.  The
timestamps and epoch data (e.g. all_poke_epoch, signal_epoch, etc.) were not
added until later.  This script will examine the TTL data, compute the
appropriate timestamp and epoch data and add these to the file.

This script is safe to run on newer versions of the file (especially if you want
the all_spout_epoch array as well) as it checks first to see if the epoch or
timestamp data is missing before adding it.

Compute RMS (compute_rms.py or launch via review GUI)
.....................................................

TODO.  Saves to <source_filename>_rms.hd5 by default.

Decimate physiology (decimate.py)
.................................

TODO.  Saves to <source_filename>_dec.hd5 by default.

Review Physiology (review_physiology.py)
........................................

Supports files with multiple physiology experiments (even though the recommended
approach is to have a single experiment per file).  This allows you to curate
the data stored in the file.  You can:

    * Truncate the end of the dataset or zero out the beginning (useful if there
      are a large number of artifacts due to the headstage falling off).

    * Mark trials as bad.  When the file is first opened in the program, a new
      column, 'valid', is added to the trial_log table.  The original trial log
      is backed up in a table called original_trial_log.  The column is an
      integer column where 1 currently means the trial is valid and 0 means it
      is invalid.  Presumably additional classifications could be added in the
      future.

Keyboard shortcuts for the plot (be sure to click on the plot to enable the
keyboard shortcuts):

    s
        jump to the beginning of the experiment
    0
        set trigger delay to zero
    up
        zoom in on the Y-axis (i.e. increase the "gain")
    down
        zoom out on the Y-axis (i.e. decrease the "gain")
    left
        scroll left
    right
        scroll right

Keyboard shortcuts for the trial log:

    up
        move to the previous trial
    down
        move to the next trial
    delete
        toggle the invalid marker for the selected trial (e.g. if the trial is
        currently marked as invalid, it will be marked as valid).

The following mouse actions are supported:

    scroll up
        zoom in on the Y-axis (i.e. increase the "gain")
    scroll down
        zoom out on the Y-axis (i.e. decrease the "gain")
    control + scroll up
        zoom in on the X-axis
    control + scroll down
        zoom out on the X-axis

Note that if you are a programmer reusing the underlying tool that supports
these actions (`cns.chaco_exts.channel_range_tool.ChannelRangeTool`) you can
override the default keyboard shortcuts.

The following actions can be performed:

    compute noise floor
        Computes the noise floor using a 16 second chunk (this can be overridden
        by the :module:`cns.setting` variable `NOISE_DURATION`)
    zero waveform
        Zeros out the physiology data before the lower bound of the visible
        screen
    truncate waveform
        Truncates the physiology data
