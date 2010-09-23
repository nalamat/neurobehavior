% Continuous play example using a serial buffer
% This program writes to the rambuffer once it has cyled half way through the buffer

RP=actxcontrol('RPco.x',[5 5 26 26]);
if RP.ConnectRZ5('GB',1)==0 disp 'Error connecting to RZ6'; end
RP.ClearCOF();
if RP.LoadCOF('MCCpTo16D.rcx')==0 disp 'Error loading circuit'; end 
RP.Run;
if bitget(RP.GetStatus,1:3)~= [1 1 1] disp 'Error, circuit not running'; 
else disp 'Circuit running'; 
end;

num_samp = 4;
RP.SetTagVal('NumSamp',num_samp);
RP.ZeroTag('buf_idx');
RP.SoftTrg(1);   
pause(1);

RP.GetTagVal('buf_idx')
a = RP.ReadTagVEX('buf', 0, num_samp*2, 'I32', 'I32', 1)

chan1 = single(a(1:4:num_samp*4))/32767
chan2 = single(a(2:4:num_samp*4))/32767
chan3 = single(a(3:4:num_samp*4))/32767
chan4 = single(a(4:4:num_samp*4))/32767
