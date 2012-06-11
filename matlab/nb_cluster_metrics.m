function [stats, fp, fn] = nb_cluster_metrics(spikes)
%   Neurobehavior by Buran BN and Sanes DH
%   
%   NB_CLUSTER_METRICS Compute spike cluster quality metrics
%
%   This is a wrapper around some of the functions provided by UMS2000 and can
%   be used to append data to the spiketimes file.
%
%   Returns
%   -------
%   stats
%       M x 6 array where each row represents the cluster and each column i sa
%       different statistic.  M is number of clusters.  Columns represent the
%       following statistics (in order)
%           lower bound of 95% CI for %RPV contaminatoin
%           upper bound of 95% CI for %RPV contaminatoin
%           expected %RPV contamination
%           actual number of RPVs
%           total number of spikes
%           probability of missing spikes based on threshold
%   fp
%       Probability of false positives
%   fn
%       Probability of false negatives

    n_clusters = size(spikes.labels, 1);
    stats = zeros(size(spikes.labels, 1), 7);

    for cluster = 1:n_clusters
        cluster_id = spikes.labels(cluster,1);
        % Returns bounds of 95% CI, expected value of % contamination and actual
        [lb, ub, p, c] = ss_rpv_contamination(spikes, cluster_id);
        indices = get_spike_indices(spikes, cluster_id);
        stats(cluster, 1:5) = [lb, ub, p, c, size(indices, 2)];

        % Returns probability of missing spike, estimate of mode for minimum
        % values, standard deviation for distribution of minimum values.
        stats(cluster, 6) = ss_undetected(spikes, cluster_id);

        % foo
        ts = spikes.unwrapped_times(indices);
        isi = diff(sort(ts));
        f2 = numel(find((isi >= 1.2e-3) & (isi < 2e-3)));
        f10 = numel(find((isi >= 2e-3) & (isi < 10e-3)));
        r = (8.8/0.8) * (f2/f10);
        stats(cluster, 7) = r;
    end

    fp = zeros(n_clusters);
    fn = zeros(n_clusters);
    for i = 1:n_clusters
        i_id = spikes.labels(i, 1);
        for j = (i+1):n_clusters
            j_id = spikes.labels(j, 1);
            C = ss_gaussian_overlap(spikes, i_id, j_id);
            fp(i,j) = C(1,1); % false positive in i (assigned from j)
            fp(j,i) = C(2,2); % false positive in j (assigned from i)
            fn(i,j) = C(1,2); % false negative in i (assigned to j)
            fn(j,i) = C(2,1); % false negative in j (assigned to i)
        end
    end
