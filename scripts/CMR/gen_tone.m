fs = 128000; %97656
fc = 1000;

% generate the flat stimulus
flat_len = .1;
flat_len = flat_len-rem(flat_len,1/fc); % make it repeatable
flat_len = flat_len - 1/fs;

t = 0:1/fs:flat_len;
y = sin(2*pi*fc*t);
plot(t, y);
xlim([0 flat_len]);
grid on;
% pause;

audiowrite('T01_flat.wav', y, fs);
% a = audioplayer([y y y y y y y y y y y y y y], fs);
% play(a);

% generate the ramp
ramp_len = 20e-3;
ramp_len = ramp_len-rem(ramp_len,1/fc); % make it repeatable

t = 0:1/fs:ramp_len;
y = sin(2*pi*fc*t) .* sin(2*pi*1/ramp_len/4*t).^2;
plot(t, y);
xlim([0 ramp_len]);
grid on;

audiowrite('T01_ramp.wav', y, fs);
