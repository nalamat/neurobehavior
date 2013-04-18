Reviewing data
--------------

Spike extraction
----------------

Events (i.e. candidate spikes) are identified based on a voltage threshold
crossing which is specified on a per-channel basis.  To determine the threshold,
the standard deviation of the signal is computed using the algorithm defined in
Quiroga et al. 2004.  

.. math::

    \sigma_n = median(|x|/0.6745)

Both the candidate threshold and artifact reject threshold are specified as a
multiple of :math:`\sigma_n`.  Whenever an event is detected (via a threshold
crossing) on any of the channels selected for extraction, the waveform from each
selected channel is pulled out (not just the one the event was detected on).
This results in a 2D array for each event, [channel, sample].  If you are
extracting a window of 30 samples from four channels, the resulting array will
be [4, 30].  

..note:: 
    The spike sorting program, UMS2000, sorts the data based on events.  This
    means that the waveform on each channel will be taken into consideration
    when classifying an event.  If you wish to sort based on the waveform from
    only a subset of the extracted channels or even a single channel you may do
    so when you load the data for processing by UMS2000.

Some Matlab functions are provided under the matlab folder for use with Matlab.
Be sure to add this folder to your Matlab path.  A function, import_ums2000, is
provided to facilitate importing the data from the extracted file into a format
that is compatible with UltraMegaSort2000, a Matlab program for clustering.  See
the documentation in the import_ums2000.m and import_spikes.m file for more
detail.

This program can handle several use-cases:

    1.  A single neuron is detected by more than one channel (i.e. you can see
        the waveform on both channels).  You can choose to extract both
        channels, but set a voltage threshold only for the channel that has the
        larger spikes (you would set the voltage threshold for the other channel
        to infinity by typing "inf" in the field).  When sorting, UMS2000 will
        take into account the waveforms on both channels when classifying the
        event.

    2.  A single neuron is detected on only one channel, but an artifact (i.e.
        movement or RF) is detection on multiple channels (including the channel
        with the neuron).  You can specify a voltage threshold for the channel
        with the spikes (setting the voltage threshold for the other channel to
        infinity).  Note that the channel used for the artifact will be
        extracted as well.  This channel could conceivably be used as additional
        input for UMS to help separate artifacts from noise or the data from
        this channel can be discarded before running the spike sorting routine.  
The simplest way to think about how UMS works is to assume that, for each event,
the waveforms from each channel are "chained" together into a single long
waveform.

The multi-step process is as follows:

    * Define the extraction settings using the review_physiology.py GUI.  Be
      sure to save the settings to the raw file (using the "Save Settings"
      option).
    * At the command-line type run the extract_spikes.py script using the raw
      file as the argument, e.g.::

        >>> python extract_spikes.py --add-rms filename_raw.hd5
      
      The `--add-rms` argument is critical for the spike censoring algorithm.
    * Once the spike extraction is complete, run the censor_spikes.py script on
      the extracted file::

        >>> python censor_spikes.py filename_extracted.hd5

      A note of caution.  The censoring algorithm can be very aggressive.  If an
      artifact is detected on *any* extracted channel (even one that has the
      spike threshold set to infinity), then it is treated as if it appears on
      all the channels.  Be sure your artifact thresholds are set properly.
    * Finally, open up Matlab and run the spike sorting.  You can see the help
      file for `nb_import_ums2000` and `nb_import_spikes` for extra detail on
      how these functions work.  Note that `nb_import_ums2000` is simply a
      wrapper around the more generic `nb_import_spikes` function and will pass
      along any unused arguments to `nb_import_spikes`.  As an example::

        >>> spikes = nb_import_ums2000('filename_extracted.hd5', 1, ...
                'channels', 1, 'spike_window', [-0.3, 1.2], ...
                'exclude_censored', true)

      I recommend excluding censored spikes.  These typically result from
      artifacts (e.g. muscle movement, sharp transients, RF dropout) and will
      tend to blur the distinction between individual clusters.  Likewise, you
      want to use a relatively narrow spike window for the waveform,
      particularly for channels that have a high rate of multiunit activity.  If
      part of an adjacent spike often appears at the beginning or end of the
      waveform, then this will generate a large number of clusters.

      The function can take a while to return since it will sort the spike
      waveforms after loading it from the file.  Once it returns, you can view
      and manipulate the clustered data using `splitmerge_tool`::

        >>> splitmerge_tool(spikes)

      Finally, once you are happy with the clusters you've identified, be sure
      to save the hand-curated spikes back to the Matlab workspace using the
      splitmerge GUI (there's a save icon in the upper left hand corner of the
      screen).  You can also save it to a Matlab file using this GUI; however, I
      recommend a few more steps before doing so::

        >>> nb_save_ums2000(spikes, 'curated')

      This will save the spiketimes file using a standard "template" that
      consists of the name of the extracted spiketimes file, the channel sorted,
      and append it with '_curated'.  In addition, it will ensure that the
      spiketimes file is saved in a format that can be read by the
      review_physiology GUI (there is an option to overlay the sorted
      spiketimes onto the raw trace).

      Finally, add some statistics about the spikes (e.g. refractory period
      violations, degree of overlap between clusters, etc.)::

        >>> nb_annotate_curated(name_of_curated_file)

      Be sure to read the docstrings for all the functions mentioned.
