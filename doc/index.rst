.. NeuroBehavior documentation master file, created by
   sphinx-quickstart on Tue Aug 17 17:22:45 2010.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to NeuroBehavior's documentation!
=========================================

Contents:

.. toctree::
   :maxdepth: 2

   getting_started.rst
   equipment.rst
   TDT_backend.rst
   experiment.rst
   aversive_behavior.rst
   positive_behavior.rst
   data_processing.rst

Python scripts and applications
===============================

If you run into memory errors when trying to decimate the waveform or extract
spikes, change the CHUNK_SIZE setting to a smaller value.  In general, you
should not encounter memory issues unless there are bad artifacts in your neural
data.  Such artifacts typically occur when the wireless headstage falls off or
is moved further away from the base station.  Since this usually occurs only at
the beginning or end of an experiment, use the truncate waveform and zero
waveform options in the review physiology program.

Review Physiology
-----------------

Supports files with multiple physiology experiments (even though the recommended
approach is to have a single experiment per file).

Keyboard shortcuts for the plot (be sure to click on the plot to enable the
keyboard shortcuts)::

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

The following mouse actions are supported::

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

The following actions can be performed::

    compute noise floor
        Computes the noise floor using a 16 second chunk (this can be overridden
        by the cns.setting variable `NOISE_DURATION`
    TODO FINISH

Matlab functions
================

.. note::

    If you have both Chronux and UltraMegaSort2000 on your Matlab path, be sure
    to remove the spikesort folder (and all subfolders) in Chronux from the path
    because this will conflict with the spike sorting algorithms provided by
    UltraMegaSort2000.  If you wish to use Chronux for spike sorting, you should
    remove UltraMegaSort2000 from the Matlab path.

    Aren't namespaces a great idea?

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
