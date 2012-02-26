function [ lfp ] = import_lfp( filename, channel, segment, field, value )
%   Neurobehavior by Buran BN and Sanes DH
%   
%   IMPORT_LFP Load lfp data from HDF5 file into Matlab
%
%   filename : string
%       Name of file containing downsampled data.  This file will typically be
%       generated via the review_physiology GUI or using the downsample.py
%       script in the Neurobehavior module.
%   channel : int
%       Channel to load
%   segment : bool
%       Segment vector into a 2D array by trial?
%
    trial_log = h5read(filename, '/block_data/trial_log');

    % Identify all the string arrays in the trial_log table and convert them to
    % cell arrays for easier parsing and handling.
    fields = fieldnames(trial_log);
    for i = 1:length(fields),
        fieldname = fields{i};
        fielddata = getfield(trial_log, fieldname);
        if ischar(fielddata),
            trial_log = setfield(trial_log, fieldname, cellstr(fielddata'));
        end
    end
    lfp.trial_log = trial_log;

    lfp.data = double(h5read(filename, '/lfp', [1, channel], [Inf, 1])');
    lfp.Fs = double(h5readatt(filename, '/lfp', 'fs'));
    lfp.q = h5readatt(filename, '/lfp', 'q');
    trial_ts = double(h5read(filename, '/block_data/physiology_epoch')');
    lfp.trial_ts = trial_ts ./ lfp.q;

end
