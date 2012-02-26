function [ lfp ] = stack_lfp( lfp, trial_mask, lb, ub )
%   Neurobehavior by Buran BN and Sanes DH
%   
%   TODO
%
 
    ts = lfp.trial_log.start(trial_mask);
    lb = round(lb * lfp.Fs);
    ub = round(ub * lfp.Fs);
    % Ugly 1-based indexing issue here.  Also, is there an equivalent of
    % Python's numpy.empty() function here?
    stacked_data = zeros(ub-lb+1, length(ts));
    for i = 1:length(ts),
        reference = round(ts(i) * lfp.Fs);
        stacked_data(:,i) = lfp.data(reference+lb:reference+ub);
    lfp.stacked_data = stacked_data;

end
