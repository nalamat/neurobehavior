function [filename] = nb_save_ums2000(spikes, file_extension)
%   Neurobehavior by Buran BN and Sanes DH
%
%   This is a simple wrapper around Matlab's save function that ensures that the
%   v7.3 format (e.g. a HDF5 container) is used for saving the data.  This
%   allows Python to read this data back in using PyTables.

    % The user did not specify the filename, so let's pull it out of the
    % spikes structure since import_ums2000 saves the filename to a field in the
    % structure.
    if nargin == 1,
        file_extension = '';
    end
    
    for i = 1:length(spikes.info.detect.detect_channels),
        ch = spikes.info.detect.detect_channels(i);
        file_extension = [file_extension '_' int2str(ch)];
    end
    filename = [spikes.base_filename '_' file_extension];
    filename = [filename '_sorted.hd5'];
    
    save(filename, '-struct', 'spikes', '-v7.3');
