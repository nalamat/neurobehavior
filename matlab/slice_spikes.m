function [spikes] = slice_spikes(spikes, lb, ub)
%   Neurobehavior by Buran BN and Sanes DH
%
%   SLICE_SPIKES Return subset of spikes, handling the slicing of all pertinent
%   arrays in the structure.  Covariance data remains unchanged, however.

    spikes.waveforms = spikes.waveforms(lb:ub,:);
    spikes.timestamps = spikes.timestamps(lb:ub);
    spikes.channels = spikes.channels(lb:ub);
    spikes.channel_indices = spikes.channel_indices(lb:ub);
    spikes.spiketimes = spikes.spiketimes(lb:ub);
    
    spikes.info.slice.lb = lb;
    spikes.info.slice.ub = ub;
