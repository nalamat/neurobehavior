from enthought.traits.api import HasTraits
from tdt import DSPCircuit
from cns import get_config
from os.path import join

class AversiveFMControllerMixin(HasTraits):

    def _setup_circuit(self):
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        circuit = join(get_config('RCX_ROOT'), 'aversive-behavior-FM')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact', 'r',
                src_type='int8', dest_type='float32', block_size=24)
        self.buffer_spout_start = self.iface_behavior.get_buffer('spout/', 'r',
                src_type='int32', block_size=1)
        self.buffer_spout_end = self.iface_behavior.get_buffer('spout\\', 'r',
                src_type='int32', block_size=1)

    def update_trial(self):
        fc = self.get_current_value('fc')
        level = self.get_current_value('level')
        speaker = self.get_current_speaker('speaker')
        if speaker == 'primary':
            att1 = self.cal_primary.get_attenuation(fc, level)
            att2 = 120.0
        elif speaker == 'secondary':
            att1 = 120.0
            att2 = self.cal_secondary.get_attenuation(fc, level)
        elif speaker == 'both':
            att1 = self.cal_primary.get_attenuation(fc, level)
            att2 = self.cal_secondary.get_attenuation(fc, level)
        self.set_attenuation(att1, att2)

    def update_intertrial(self):
        pass

    def set_depth(self, value):
        self.iface_behavior.set_tag('depth', value)

    def set_fc(self, value):
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.iface_behavior.set_tag('cf', coerced_value)
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))
        self.set_current_value('cf', coerced_value)

    def set_fm(self, value):
        self.iface_behavior.set_tag('fm', value)

    def set_level(self, value):
        cf = self.get_current_value('cf')
        att = self.cal_primary.max_spl(cf)-level
        self.iface_behavior.set_tag('att_A', att)
