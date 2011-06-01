RP = actxserver('RPco.x')
RP.ConnectRZ6('GB', 1)
RP.LoadCOF('positive-behavior-BAD.rcx')
RP.Run
bitget(RP.GetStatus,1:3)
RP.ZeroTag('speaker')
pause(0.1);
bitget(RP.GetStatus,1:3)
