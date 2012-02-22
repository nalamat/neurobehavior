function [spikes] = sort_spikes(spikes)
%   Neurobehavior by Buran BN and Sanes DH
%
%   SORT_SPIKES Run the spike sorting functions

    spikes = ss_align(spikes);
    spikes = ss_kmeans(spikes);
    spikes = ss_energy(spikes);
    spikes = ss_aggregate(spikes);
