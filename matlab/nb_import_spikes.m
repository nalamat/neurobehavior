function [spikes] = nb_import_spikes(filename, varargin)
%   Neurobehavior by Buran BN and Sanes DH
%
%   NB_IMPORT_SPIKES Load spike waveforms from HDF5 file into Matlab and cleans
%   up the data.  This is mainly a helper function for import_chronux and
%   import_ums2000 but can be used directly if desired.
%
%   Be sure to review the inline documentation in review_physiology.py for
%   the extract_features method before editing this code as there is
%   additional documentation regarding the structure of the HDF5 file
%   there.
%
%   Required arguments
%   ------------------
%   filename : string
%       name of file to load data from (must be generated by the
%       review_physiology.py script in the neurobehavior module).
%
%   Optional arguments
%   ------------------
%   channels : array (default - all channels)
%       Specify the default values for waveform_channels and detect_channels.
%       Mainly a convenience argument that allows you to call the function as:
%           >>> sp = nb_import_spikes(filename, 'channels', 3);
%       In lieu of the more verbose syntax:
%           >>> sp = nb_import_spikes(filename, 'detect_channels', 3, ...
%                                     'waveform_channels', 3);
%       If empty, this means to return all channels.
%
%   waveform_channels : array (defaults to value passed in 'channels')
%       For each event include only the waveforms from these channels
%
%   detect_channels : array (defaults to value passed in 'channels')
%       Include only events that were detected on at least one of these channels
%
%   exclude_censored : boolean (default False)
%       Omit censored spikes from the sorting.  Requires that the
%       censor_spikes.py script be run on the extracted spiketimes file.  In 99%
%       of cases, you want to set this option to True.
%
%   trial_range : Empty or length 2 (lower, upper)
%       If not empty, return only events that occur during a trial.  The lower
%       and upper bound indicate how many seconds before and after the trial to
%       include.  
%           (-1, 1)
%               One second before to one second after
%           (0, 1)
%               Start of trial to one second after end of trial
%           (1, 2)
%               One second after start of trial to one second after end of 
%               trial
%       Trial times could be obtained from the physiology_epoch block.  However,
%       older datafiles did not save these times, so they will be obtained from
%       the less accurate trial_log column, 'start'.  Eventually, this code can
%       be updated to use the physiology_epoch block instead.
%
%   DEBUGGING ARGUMENTS (do not use these unless you are attempting to
%   troubleshoot some issues with the spike sorting)
%
%   max_features : integer (default inf)
%       Maximum number of events to return (useful for debugging since the
%       clustering algorithms can often be slow when working with a large number
%       of features).  The entire dataset is loaded into memory before
%       truncating it so if you're running into memory issues when attempting to
%       load the data, setting max_features will not help.
%
%   waveform_gain : float (default 1)
%       Scale the spike waveform (included only for debugging purposes to see
%       whether the spike sorting routines are affected by the absolute
%       amplitude, or if they only care about the relative amplitude).
%
%   Returns struct containing spike waveform data (waveforms, indices and
%   event times) that just needs a tiny bit of tweaking before it is 100%
%   compatible with UMS2000 or Chronux.
%
%   TODO: Complete documenting the fields of the structure... (volunteers?)
%
%   spikes.source_indices (one-based)
%       Index of the event in the source file.  Useful for reintegrating the
%       sorted information with the source dataset since we typically pull out
%       only a subset of this data.
%   spikes.timestamps
%   spikes.channels
%   spikes.waveforms
%   spikes.info.detect.extracted_channels
%   spikes.info.detect.trial_epoch
%       Lower and upper bound (in seconds) of each trial as computed by the data
%       acquisition program
%   spikes.info.detect.trial_epoch_expanded
%       Lower and upper bound (in seconds) of spikes included in each trial.

    % Let the inputParser handle massaging the input into the format we need and
    % setting default values as required.  This is a lot of work that Python
    % handles under the hood by default.
    p = inputParser();
    p.addRequired('filename', @ischar);
    p.addParamValue('channels', [], @isvector);
    p.addParamValue('waveform_channels', [], @isvector);
    p.addParamValue('detect_channels', [], @isvector);
    p.addParamValue('max_features', inf, @isscalar);
    p.addParamValue('exclude_censored', false, @islogical);
    p.addParamValue('omit_prepost', true, @islogical);
    p.addParamValue('trial_range', [], ...
                    @(x) isvector(x) && (length(x) == 2 || isempty(x)) ...
                   );
    p.addParamValue('waveform_gain', 1, @isscalar);
    p.parse(filename, varargin{:});

    % Now, let's copy the results to the local namespace and get on with
    % the real work of this function.
    filename = p.Results.filename;
    waveform_channels = p.Results.waveform_channels;
    detect_channels = p.Results.detect_channels;
    max_features = p.Results.max_features;
    trial_range = p.Results.trial_range;
    waveform_gain = p.Results.waveform_gain;
    exclude_censored = p.Results.exclude_censored;

    % Empty arrays means that the user wants to default to the value specified
    % via the channels argument.  If channels is also empty, this defaults to
    % loading events and waveforms from all channels.
    if isempty(waveform_channels),
        waveform_channels = p.Results.channels;
    end
    if isempty(detect_channels),
        detect_channels = p.Results.channels;
    end

    % Finally, we get to work on loading our data.
    
    % NOTE - All vectors are transposed so the shape is 1xN rather than Nx1
    % (which is how they appear to Matlab when loaded from the HDF5 file).
    % 1xN is required by some of UMS2000's functions for no good reason
    % other than the fact it was written in Matlab.
    
    extracted_channels = h5readatt(filename, '/event_data', 'extracted_channels');
    spikes.info.detect.extracted_channels = double(extracted_channels');
    
    % Indices of the threshold crossing in the raw waveform.  To compute the
    % time of the threshold crossing relative to the start of the experiment,
    % divide the indice by the sampling frequency or just read the data stored
    % in /event_data/timestamps which is in units of seconds.
    timestamps = double(h5read(filename, '/event_data/timestamps_n')');
    timestamps_fs = h5readatt(filename, '/event_data/timestamps_n', 'fs');
    timestamps_fs = double(timestamps_fs);

    % Indices of the events in the file (one-based).  Since we may be sorting a
    % subset of our data, we need to be able to pair up the sorted results with
    % the original dataset.
    source_indices = 1:length(timestamps);
    
    % The ordering of the array is C-continguous in the HDF5 file (e.g. the
    % NumPy default if you don't specify an order when creating the array).
    % Matlab requires all arrays to be Fortran-ordered, so this causes some
    % swapping of the axes when reading in the data.  Waveforms must be a
    % 3d array of [events, window_samples, channels].  By default, h5read
    % loads them as [window_samples, channels, events].  Next, we unstack
    % the waveforms so that it is essentially a 2D array of [events,
    % window_samples] where the waveform from each channel has been merged
    % into a single continuous waveform.
    if isempty(waveform_channels)
        waveform_channels = extracted_channels;
    end

    % But, first, we need to load the waveforms on a channel-by-channel basis.
    % This is because some of the extracted arrays can extremely large, and
    % Matlab runs into memory issues if we attempt to load the entire waveform
    % array into memory before pulling out the channels we are interested in.
    extract_indices = get_indices(waveform_channels, extracted_channels);
    spikes.info.detect.extract_indices = extract_indices;

    % Find out how big the waveforms array is and preallocate an array of the
    % correct size
    waveforms_info = h5info(filename, '/event_data/waveforms');
    waveforms_size = waveforms_info.Dataspace.Size;
    waveforms_size(2) = length(extract_indices);
    waveforms = zeros(waveforms_size);

    % Loop through and pull the data into our preallocated array
    for i=1:length(extract_indices)
        waveforms(:,i,:) = h5read(filename, '/event_data/waveforms', ...
                                  [1 extract_indices(i) 1], [Inf 1 Inf]);
    end

    % Fix the ordering issues
    waveforms = permute(waveforms, [3, 1, 2]);
    waveforms = waveforms * waveform_gain;

    % Channel on which the event was detected
    channels = double(h5read(filename, '/event_data/channels')');
    channel_indices = double(h5read(filename, '/event_data/channel_indices')');
    
    % Now, if the user wants events requested only if they were detected on
    % certain channels, return those.
    if ~isempty(detect_channels),
        detect_mask = zeros(1, length(waveforms));
        for ch = detect_channels,
            detect_mask = detect_mask | (channels == ch);
        end

        % Winnow down our dataset based on the detect_mask
        waveforms = waveforms(detect_mask, :, :);
        timestamps = timestamps(detect_mask);
        channels = channels(detect_mask);
        channel_indices = channel_indices(detect_mask);
        source_indices = source_indices(detect_mask);
    else
        detect_channels = extracted_channels;
        detect_mask = ones(size(timestamps));
    end
 
    % Load the censor data.  We can't apply the censor mask quite yet since we
    % need to winnow it down first.
    if exclude_censored
        censored = h5read(filename, '/event_data/censored')';
        censored = censored(detect_mask);
        waveforms = waveforms(~censored, :, :);
        timestamps = timestamps(~censored);
        channels = channels(~censored);
        channel_indices = channel_indices(~censored);
        source_indices = source_indices(~censored);
    end
    
    if length(trial_range) == 2, 
        % Load the start/end times of each trial and convert to the same
        % unit as the timestamps_n array (e.g. the unit is 1/sampling 
        % frequency of the physiology data).
        trial_log = h5read(filename, '/block_data/trial_log');

        % Apparently Matlab's h5read doesn't like "end" as a fieldname for the
        % trial_log structure and converts it to xEnd (even though "end" is a
        % valid fieldname, go figure).
        epochs = round([trial_log.start, trial_log.xEnd] * timestamps_fs)';
        spikes.info.detect.trial_epochs = epochs;
    
        lb = round(trial_range(1)*timestamps_fs);
        ub = round(trial_range(2)*timestamps_fs);

        % Unlike Python's Numpy, this triggers a *copy* of the entire array,
        % meaning that expanded_epochs does not point to the same object as
        % epochs.
        expanded_epochs = epochs;
        expanded_epochs(1,:) = expanded_epochs(1,:)+lb;
        expanded_epochs(2,:) = expanded_epochs(2,:)+ub;
        spikes.info.detect.expanded_trial_epochs = expanded_epochs;

        % Filter the event data by including only events that fall in the
        % range [trial_start+trial_range(1), trial_end+trial_range(2))
        trial_mask = zeros(1, length(timestamps));
        for i = 1:length(expanded_epochs),
            submask = (timestamps >= expanded_epochs(1,i)) & ...
                      (timestamps < expanded_epochs(2,i));
            trial_mask = trial_mask | submask;
        end

        % Winnow down our dataset to those that are within the trial range
        waveforms = waveforms(trial_mask, :, :);
        timestamps = timestamps(trial_mask);
        channels = channels(trial_mask);
        channel_indices = channel_indices(trial_mask);
        source_indices = source_indices(trial_mask);
    end

    % Information saved in spikes.info.detect.settings reflects the actual
    % arguments passed to the function, not the values that were actually used
    % so we should save both p.Results as well as *_channels.
    spikes.info.detect.settings = p.Results;
    spikes.info.detect.detect_channels = detect_channels;
    spikes.info.detect.waveform_channels = waveform_channels;
    spikes.info.detect.window_samples = size(waveforms, 2);
    spikes.info.detect.source_file = filename;
    
    % Truncate the list of event times.  First, if we have fewer events than
    % max_features, then update max_features accordingly.  This is only for
    % debugging purposes.
    if ~isinf(max_features) & (max_features < length(timestamps)),
        waveforms = waveforms(1:max_features, :, :);
        timestamps = timestamps(1:max_features);
        channels = channels(1:max_features);
        channel_indices = channel_indices(1:max_features);
        source_indices = source_indices(1:max_features);
    end

    spikes.waveforms = waveforms;
    spikes.timestamps = timestamps;
    spikes.channels = channels;
    spikes.channel_indices = channel_indices;
    spikes.source_indices = source_indices;
    spikes.trials = [1];
    spikes.spiketimes = timestamps ./ timestamps_fs;
    spikes.unwrapped_times = spikes.spiketimes;
    spikes.trials = ones(1, length(spikes.timestamps), 'single');
end

function [indices] = get_indices(channels, available_channels)
    % Map the channel number to the corresponding channel index in the
    % spikes.waveforms array. 
    indices = zeros(1, length(channels));
    for i = 1:length(channels),
        index = find(available_channels == channels(i));
        if ~isscalar(index),
            err = MException('Neurobehavior:InvalidChannel', ...
                             'Channel not available for extraction');
            throw(err);
        end
        indices(i) = index;
    end
end
