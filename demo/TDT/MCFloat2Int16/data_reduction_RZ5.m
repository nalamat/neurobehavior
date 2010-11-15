RP=actxserver('RPco.x')
%ccc
%RP=actxcontrol('RPco.x',[5 5 26 26]);
if RP.ConnectRZ5('GB',1)==0 disp 'Error connecting to RZ2'; end
RP.ClearCOF();
if RP.LoadCOF('data_reduction_RZ5.rcx')==0 disp 'Error loading circuit'; end 
RP.Run;
if bitget(RP.GetStatus,1:3)~= [1 1 1] disp 'Error, circuit not running'; 
else disp 'Circuit running'; 
end;

num_samp = 4;
channels = 16;
RP.SetTagVal('nHi',num_samp);

disp(['mc_idx is ', num2str(RP.GetTagVal('mc_idx'))])
disp(['mc16_idx is ', num2str(RP.GetTagVal('mc16_idx'))])
disp(['mc8_idx is ', num2str(RP.GetTagVal('mc8_idx'))])
disp(['Triggering now, nHi/num_samp is set to ', num2str(num_samp)])
RP.SoftTrg(1);   
pause(1);

disp(['mc_idx is ', num2str(RP.GetTagVal('mc_idx'))])
disp(['mc16_idx is ', num2str(RP.GetTagVal('mc16_idx'))])
disp(['mc8_idx is ', num2str(RP.GetTagVal('mc8_idx'))])

disp 'Acquiring values from an 16-channel MCSerStore buffer'
a = RP.ReadTagVEX('mc', 0, num_samp, 'F32', 'F32', channels)

disp 'Acquiring values from an 16-channel MCFloat2Int16/MCSerStore buffer'
a = single(RP.ReadTagVEX('mc16', 0, num_samp, 'I16', 'I16', channels))/6553

disp 'Acquiring values from an 16-channel MCFloat2Int8/MCSerStore buffer'
a = single(RP.ReadTagVEX('mc8', 0, num_samp, 'I8', 'I8', channels))/30
