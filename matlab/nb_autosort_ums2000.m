function nb_autosort_ums2000(filenames, basepath, varargin)
%   Neurobehavior by Buran BN and Sanes DH
%
%   NB_AUTOSORT_UMS2000 Run UMS2000 on each channel in the datafile using the given
%   settings specified by varargin.  See IMPORT_UMS2000 and IMPORT_SPIKES for
%   more detail on the arguments that can be passed to varargin.  This function
%   sets the 'detect_channels' and 'waveform_channels' option string, so don't
%   attempt to set these.
%
%   Will automatically sort each channel independently of the others.  If you
%   have more specific requirements, you will have to write your own autosort
%   script.
%
%   If the input filename is "110911_G1_tail_behavior_extracted.hd5", the output
%   filename will be "110911_G1_tail_behavior_{ch}_initial_sort.mat" where {ch}
%   is the channel number.
%
%   If the output file already exists, the sorting step will be skipped (this is
%   handy for cases where the sorting program crashes).
%
%   HINT: Use Matlab's dir function in conjunction with wildcards to quickly
%   generate your list of filenames, e.g.::
%       
%       filenames = dir('d:/data/*_extracted.hd5');
%       nb_autosort_ums2000(filenames, 'artifact_reject', 'all');
%       % Now, go get some coffee.  It's going to be a while.
% 
%   Required arguments
%   ------------------
%   filenames : struct array with the name field pointing to the filename
%       List of filenames to process.  This expects the filenames to be in the
%       format returned by Matlab's dir() function (see the docstring of dir()
%       for more detail).  Unfortuantely, dir() doesn't make life super-simple
%       since it only returns the filenames, not the absolute or relative path
%       to the file, so you need to provide the path to the folder (see next
%       argument).
%   basepath : path to list of files specified in filenames
%
%   All remaining arguments are passed to nb_import_ums2000
%

for i = 1:length(filenames),
    if ~strcmpi(basepath, '')
        filename = [basepath, '/', filenames(i).name];
    else
        filename = filenames(i).name;
    end
    base_filename = regexprep(filename, '(.*)\.(h5|hd5|hdf5)', '$1');

    for channel = nb_extracted_channels(filename),
        files = dir([base_filename '__' int2str(channel) '_sorted*.mat']);
        if length(files) == 0
            fprintf('Sorting %s channel %d.', filenames(i).name, channel);
            spikes = nb_import_ums2000(filename, 0, ...
                'channels', channel, varargin{:});
            spikes = ss_align(spikes);
            spikes = ss_kmeans(spikes);
            spikes = ss_energy(spikes);
            spikes = ss_aggregate(spikes);
            nb_save_ums2000(spikes);
            fprintf('  Success!\n');
        else
            fprintf('%s channel %d already sorted.\n', filenames(i).name, channel);
        end
    end
end
