function nb_annotate_curated(filenames, basepath)
%   Neurobehavior by Buran BN and Sanes DH
%   
%   NB_ANNOTATE_CURATEE Add cluster metrics to sorted spiketimes file

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
