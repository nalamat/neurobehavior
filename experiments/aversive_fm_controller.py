from tdt import DSPCircuit

from abstract_aversive_controller import AbstractAversiveController

from cns import RCX_ROOT
from os.path import join

class AversiveFMController(AbstractAversiveController):

    def setup_experiment(self, info):
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        circuit = join(RCX_ROOT, 'aversive-behavior-FM')
        self.iface_behavior = DSPCircuit(circuit, 'RZ6')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact', 'r',
                src_type='int8', dest_type='float32', block_size=24)

    # We are overriding the three signal update methods (remind, warn, safe) to
    # work with the specific circuit we constructed
    def update_remind(self):
        self.iface_behavior.set_tag('depth', self.current_remind.parameter)

    def update_warn(self):
        self.iface_behavior.set_tag('depth', self.current_warn.parameter)

    def update_safe(self):
        pass

    def set_carrier_frequency(self, value):
        self.iface_behavior.set_tag('cf', value)

    def set_modulation_frequency(self, value):
        self.iface_behavior.set_tag('fm', value)
