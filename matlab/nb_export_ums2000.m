function [] = nb_export_ums2000(spikes, node_name)
%   Neurobehavior by Buran BN and Sanes DH
%
%   Save cluster and cluster label data back to extracted file for further
%   analysis.

    % Really, auto-calls are a bit
    if nargin() == 1;
        node_name = '';
    end

    filename = spikes.info.detect.source_file;
    source_size = length(spikes.info.detect.source_mask);
    assigns_path = [node_name '/assigns'];
    labels_path = [node_name '/labels'];

    % Check to see if the assigns array already exists.  If not, create it
    % (h5info will raise an exception if it is missing).  I'm not sure of a
    % better way to check for the presence of the array other than attempting to
    % access it and see if I get an exception.  Ironically, this is a
    % somewhat Pythonic approach as well.
    try
        h5info(filename, assigns_path);
    catch
        h5create(filename, assigns_path, source_size, 'Datatype', 'int32');
    end

    % If assigns exists, labels probably exists as well so it is probably
    % unecessary to break this out into a second try/catch block.  However, this
    % is probably a more robust approach.
    try
        h5info(filename, labels_path);
    catch
        h5create(filename, labels_path, source_size, 'Datatype', 'int32');
    end

    assigns = zeros([1, source_size], 'int32');
    assigns(spikes.source_indices) = spikes.assigns;

    % Labels will be 1 .. 4 depending on the mapping with UMS2000's array of
    % optional labels for each cluster.  If 0, this means that the spike was not
    % included in the sorting.  If -1, the spike is an outlier.
    labels = zeros([1, source_size], 'int32');
    for i = spikes.labels'
        assign = i(1);
        label = i(2);
        labels(assigns==assign) = label;
    end

    if isfield(spikes.info, 'outliers')
        outliers = spikes.info.outliers;
        assigns(outliers.source_indices) = -1;
        labels(outliers.source_indices) = -1;
    end

    h5write(filename, assigns_path, assigns);
    h5write(filename, labels_path, labels);

    % Save some information about what clusters are available and their labels
    h5writeatt(filename, node_name, 'cluster_ids', spikes.labels(:,1));
    h5writeatt(filename, node_name, 'cluster_labels', spikes.labels(:,2));

    % Now, save the label names.  Matlab's HDF5 support for strings is not very
    % good, so we need to hack it on a bit.
    labels = spikes.params.display.label_categories;
    for i=1:length(labels)
        attrname = ['cluster_label_' int2str(i)];
        h5writeatt(filename, '/event_data', attrname, labels{i});
    end
