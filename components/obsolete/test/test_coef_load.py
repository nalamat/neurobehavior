import logging
log = logging.getLogger()
log.setLevel(logging.DEBUG)

from cns import equipment
from numpy import array

try:
    circuit = equipment.dsp().load('test/physiology_test_v2', 'RZ5')
    diff_map = [2, 0, 0, 0, 0 -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    circuit.diff_map.set(diff_map)
    circuit.start()

    raw_input("Hit enter when you're done")

except equipment.EquipmentError, e:
    print "Error loading circuit"
    print "The exact error message was ", e
