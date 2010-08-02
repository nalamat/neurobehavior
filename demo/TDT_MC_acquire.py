from cns import equipment
import numpy as np
import time

RX6 = equipment.backend.load('test_comp_mc', 'RX6')
RX6.open('contact_buf', src_type=np.int8, channels=5, sf=127)
RX6.start()

for i in range(5):
    print 'sleeping'
    time.sleep(.3)
    print RX6.contact_buf.next()
