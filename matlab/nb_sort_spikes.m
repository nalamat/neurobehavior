function [spikes] = nb_sort_spikes(spikes)
%   Neurobehavior by Buran BN and Sanes DH
%
%   NB_SORT_SPIKES Run the spike sorting functions

    spikes = ss_align(spikes);
    spikes = ss_kmeans(spikes);
    spikes = ss_energy(spikes);
    spikes = ss_aggregate(spikes);
