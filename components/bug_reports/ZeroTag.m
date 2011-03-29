RP = actxcontrol('RPco.x', [5 5 26 26]);
%RP = actxserver('RPco.x');
if RP.ConnectRZ6('GB', 1) == 0 disp 'connect error'; end
if RP.LoadCOF('ZeroTag_example.rcx') == 0 disp 'load error'; end
if RP.Run == 0 disp 'run error'; end
bitget(RP.GetStatus,1:3)
if bitget(RP.GetStatus,1:3)~=[1 1 1] disp 'error'; end
if RP.ZeroTag('buffer') disp 'ZeroTag error'; end
bitget(RP.GetStatus,1:3)
