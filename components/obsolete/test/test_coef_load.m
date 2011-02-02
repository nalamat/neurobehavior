RP=actxserver('RPco.x');

if RP.ConnectRZ5('GB',1)==0 disp 'Error connecting to RZ5'; end
RP.ClearCOF();
if RP.LoadCOF('physiology_test_v2.rcx')==0 disp 'Error loading circuit'; end 
RP.Run;
if bitget(RP.GetStatus,1:3)~= [1 1 1] disp 'Error, circuit not running'; 
else disp 'Circuit running'; 
end;

matrix = [1 0 0 0 0 -1 0 0 0 0 0 0 0 0 0 0];
RP.WriteTagV('diff_map', 0, matrix);
RP.ReadTagV('diff_map', 0, 16)