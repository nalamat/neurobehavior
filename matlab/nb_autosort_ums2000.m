function nb_autosort_ums2000(filenames, varargin)
%   Neurobehavior by Buran BN and Sanes DH
%
%   NB_AUTOSORT_UMS2000 Run UMS2000 on each channel in the datafile using the given
%   settings specified by varargin.  See IMPORT_UMS2000 and IMPORT_SPIKES for
%   more detail on the arguments that can be passed to varargin.  This function
%   uses 'detect_channels' and 'waveform_channels', so don't attempt to set
%   these.
%
%   Will automatically sort each channel independently of the others.
%
%   Required arguments
%   ------------------
%   filenames : cell array of strings
%       List of filenames to process

for i = 1:length(filenames),
    filename = filenames{i};
    filename
    channels = double(h5read(filename, '/extracted_channels'));
    for j = 1:length(channels),
        channel = channels(j);
        channel
        sp = import_ums2000(filename, 1, 'detect_channels', channel, ...
            'waveform_channels', channel, varargin{:});
        save([sp.base_filename '_' int2str(channel) '_initial_sort.mat'], 'sp');
    end
end
