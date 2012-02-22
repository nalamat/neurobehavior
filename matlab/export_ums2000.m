function [spikes] = export_ums2000(spikes, filename)
%   Neurobehavior by Buran BN and Sanes DH
%
%   EXPORT_UMS2000 sorted data back to the *_extracted HDF5 file
%
%   EXPORT_UMS2000(spikes) saves cluster data to the original file the waveforms
%   were loaded from.  EXPORT_UMS2000(spikes, filename) saves the cluster data
%   to the specified filename.
 
    % The user did not specify the filename, so let's pull it out of the
    % spikes structure since import_ums2000 saves the filename to a field in the
    % structure.
    if nargin == 1,
        filename = spikes.info.detect.source_file;
    end

    % Transform the assigns array so it is in the same orientation as the other
    % data already stored in the HDF5 file.  This is the array containing the
    % cluster ID of each event.
    shape = size(spikes.info.detect.source_mask);
    h5create(filename, '/sort/clusters', shape, 'FillValue', nan);
    %h5write(filename, '/sort/clusters', spikes.assigns');

    % Label for each cluster (Matlab's HDF5 functions do not support writing
    % string data to a HDF5 file, so we can't assign the proper labels used in
    % the GUI.  Awesome.
    %h5create(filename, '/sort/cluster_labels', spikes.labels);

    % There is additional information we could write to the file, but this is
    % sufficient for now.
