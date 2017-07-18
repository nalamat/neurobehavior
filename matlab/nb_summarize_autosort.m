function nb_summarize_autosort(filenames, basepath, varargin)
%   Neurobehavior by Buran BN and Sanes DH
%
%   NB_AUTOSORT_UMS2000 Given the sorted data, save some figures (in PNG format)
%   summarizing the available clusters.  This is useful for quickly scanning a
%   large dataset to make a decision about which files you'd like to focus on.

for i = 1:length(filenames)
    if ~strcmpi(basepath, '')
        filename = [basepath, '/', filenames(i).name];
    else
        filename = filenames(i).name;
    end
    base_filename = regexprep(filename, '(.*)\.(mat)', '$1');
    spikes = load(filename)
    plot_features(spikes);
    saveas(gcf(), [base_filename '_features'], 'png');
    for i = 1:size(spikes.labels, 1)
        cluster = spikes.labels(i,1);
        plot_detection_criterion(spikes, cluster);
        saveas(gcf(), [base_filename, '_d_' int2str(cluster)], 'png');
    end
end
