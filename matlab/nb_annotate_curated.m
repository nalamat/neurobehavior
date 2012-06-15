function nb_annotate_curated(curated_filename)
%   Neurobehavior by Buran BN and Sanes DH
%   
%   NB_ANNOTATE_CURATEE Add cluster metrics to sorted spiketimes file

    spikes = open(curated_filename);
    [stats, fp, fn] = nb_cluster_metrics(spikes); 
    spikes.cluster_stats = stats;
    spikes.cluster_fp = fp;
    spikes.cluster_fn = fn;
    save(curated_filename, '-struct', 'spikes', '-v7.3');

