function [ spikes ] = import_chronux( filename )

%   IMPORT_CHRONUX Load spike waveforms from HDF5 file into Matlab
%
%   filename : string
%       name of file to load data from (must be generated by the
%       review_physiology.py script in the neurobehavior module).
%
%   Returns struct containing spike waveform data that can be used directly by
%   Chronux.

    spikes = import_spikes(filename);
    spikes.Fs = double(h5readatt(filename, '/', 'fs'));

    % Collapse the waveform across channels so a single event is viewed as the
    % composite waveform across all channels.
    spikes.waveforms = spikes.waveforms(:,:);
    % transpose b/c of error in ss_aggregate when array is the other way
    spikes.spiketimes = spikes.indices'./spikes.Fs; 

    align_sample = double(h5readatt(filename, '/', 'samples_before')+1.0);
    spikes.threshT = align_sample;
    spikes.thresh = double(h5readatt(filename, '/', 'threshold'));
end
