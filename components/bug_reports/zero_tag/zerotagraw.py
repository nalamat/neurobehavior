from tdt.actxobjects import RPcoX
import numpy as np
RP = RPcoX()
data = np.ones(10)
print RP.ConnectRZ6('GB', 1)
print RP.LoadCOF('positive-behavior-BAD.rcx')
print RP.Run()
print RP.GetStatus()
print RP.ReadTagV('speaker', 0, 10)
print RP.ZeroTag('speaker')
#print RP.ZeroTag('buffer')
print RP.SetTagVal('to_safe_n', 131)
print RP.GetTagVal('to_safe_n')
#pause(0.1);
print RP.GetStatus()
#bitget(RP.GetStatus,1:3)
