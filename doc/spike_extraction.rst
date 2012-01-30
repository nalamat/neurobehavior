Spike extraction
----------------

Events are identified based on a simple threshold crossing.  This threshold can be configured on a per-channel basis as can the artifact reject threshold.  Thresholds are defined as the number of standard deviations above or below the noise floor.  Noise floor is computed using a median algorithm.  

Whenever an event is detected (via a threshold crossing) on any of the channels selected for extraction, the waveform from each selected channel is pulled out (not just the one the event was detected on).  This results in a 2D array for each event, [channel, sample].  If you are extracting a window of 30 samples from four channels, the size will be [4, 30].  

..note:: 
    The spike sorting program, UMS2000, sorts the data based on events.  This
    means that the waveform on each channel will be taken into consideration
    when classifying an event.  If you wish to sort based on the waveform from
    only a subset of the extracted channels or even a single channel you may do
    so when you load the data for processing by UMS2000.

This program can handle several use-cases

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
