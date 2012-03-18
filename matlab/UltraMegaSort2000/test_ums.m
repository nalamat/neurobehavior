x = h5read('c:\users\brad\desktop\ums2000_test.hd5', '/signal', [1, 1], [inf, 1]);
fs = 25e3;

% create dummy cell array as if the entire waveform was one trial
c = {};
c{1} = x;

sp = ss_default_params(fs);
sp.params.thresh = -4.0;
sp = ss_detect(c, sp);

t = (1:25e3)./ 25e3;

close('all');

figure(1);
hold('on');
plot(t, x(1:25e3, 1));
%plot(sp.spiketimes, zeros(size(sp.spiketimes)), 'ro');
plot([0, 1], [sp.info.detect.thresh, sp.info.detect.thresh], 'k-');

%figure(2);
%plot(sp.waveforms(1:, :, 1)');