function [errors] = nb_annotate_curated(filenames, basepath)
%   Neurobehavior by Buran BN and Sanes DH
%   
%   NB_ANNOTATE_CURATEE Add cluster metrics to sorted spiketimes file
% 
%   Parameters
%   ----------
%   filenames : list of filenames 
%       This will accept the default output generated by the dir function
%   basepath : path to location of files
%       Since Matlab's dir function returns only the basename (i.e. the
%       filename) but not the path to the file, you need to provide the path
%       (either absolute or relative).
%
%   Returns
%   -------
%   errors
%       List of filenames that it was unable to process

    errors = {};
    if isstruct(filenames)
        for i = 1:length(filenames)
            filename = filenames(i).name;
            if ~strcmpi(basepath, '')
                filename = [basepath, '/', filenames(i).name];
            else
                filename = filenames(i).name;
            end
            try
                annotate_curated(filename);
            catch
                errors{end+1} = filename;
                fprintf('Unable to annotate file %s\n', filename);
            end
        end
    else
        annotate_curated(filenames);
    end
end

function annotate_curated(curated_filename)
    spikes = open(curated_filename);
    [stats, fp, fn] = nb_cluster_metrics(spikes); 
    spikes.cluster_stats = stats;
    spikes.cluster_fp = fp;
    spikes.cluster_fn = fn;
    save(curated_filename, '-struct', 'spikes', '-v7.3');
end