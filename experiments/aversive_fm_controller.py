from tdt import DSPCircuit

from abstract_aversive_controller import AbstractAversiveController

class AversiveFMController(AbstractAversiveController):

    def init_equipment(self):
        # I have broken this out into a separate function because
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        self.iface_behavior = DSPCircuit('components/aversive-behavior-FM', 'RZ6')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact',
                src_type='int8', dest_type='float32', block_size=24)

        self.set_carrier_frequency(self.model.paradigm.carrier_frequency)
        self.set_modulation_frequency(self.model.paradigm.modulation_frequency)

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
