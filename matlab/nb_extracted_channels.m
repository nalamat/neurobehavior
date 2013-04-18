function [channels] = nb_extracted_channels(filename)
%   Neurobehavior by Buran BN and Sanes DH
%
%   NB_EXTRACTED_CHANNELS Return list of extracted channels stored in file
%
%   Excludes channels for which threshold is not finite
%
%   Required arguments
%   ------------------
%   filename : string
%       Name of file to query for extracted data

    channels = h5readatt(filename, '/event_data', 'extracted_channels');
    thresholds = h5readatt(filename, '/event_data', 'threshold');
    channels = double(channels');
    channels = channels(isfinite(thresholds));
