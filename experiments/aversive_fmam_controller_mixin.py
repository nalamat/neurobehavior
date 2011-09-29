from enthought.traits.api import HasTraits
from tdt import DSPCircuit
from cns import get_config
from os.path import join
from neurogen.block_definitions import SAM

class AversiveFMAMControllerMixin(HasTraits):

    def _setup_circuit(self):
        # AversiveFMController needs to change the initialization sequence a
        # little (i.e. it needs to use different microcode and the microcode
        # does not contain int and trial buffers).
        circuit = join(get_config('RCX_ROOT'), 'aversive-behavior-FMAM')
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
        pass

    def update_intertrial(self):
        pass

    def set_fm_depth(self, value):
        self.iface_behavior.set_tag('fm_depth', value)

    def set_fm_freq(self, value):
        self.iface_behavior.set_tag('fm_freq', value)

    def set_fm_direction(self, value):
        # This is linked to a Tone component that generates a sinusoid wave that
        # controls the instantaneous frequency of actual tone.  To get a
        # positive upsweep in frequency, set the starting phase to 0.  To get a
        # negative downsweep in frequency, set the starting phase to pi.  In
        # either case, sin(phase) **must** evaluate to 0 to ensure there are no
        # discontinuities in transitioning from the intertrial to trial signal.
        if value == 'positive':
            self.iface_behavior.set_tag('fm_phase', 0)
        elif value == 'negative':
            self.iface_behavior.set_tag('fm_phase', np.pi)

    def set_am_direction(self, value):
        self._update_am()

    def set_am_depth(self, value):
        self._update_am()

    def set_am_freq(self, value):
        self.iface_behavior.set_tag('am_freq', value)

    def _update_am(self):
        am_direction = self.get_current_value('am_direction')
        am_depth = self.get_current_value('am_depth')

        am_amplitude = am_depth/2.0
        am_shift = 1-am_amplitude
        am_phase = SAM.eq_phase(am_depth, am_direction)
        am_sf = 1.0/SAM.eq_power(am_depth)

        self.iface_behavior.set_tag('am_amplitude', am_amplitude)
        self.iface_behavior.set_tag('am_shift', am_shift)
        self.iface_behavior.set_tag('am_phase', am_phase)
        self.iface_behavior.set_tag('am_sf', am_sf)

    def set_fc(self, value):
        coerced_value = self.cal_primary.get_nearest_frequency(value)
        self.iface_behavior.set_tag('fc', coerced_value)
        mesg = 'Coercing {} Hz to nearest calibrated frequency of {} Hz'
        self.notify(mesg.format(value, coerced_value))
        self.set_current_value('fc', coerced_value)

    def set_level(self, value):
        speaker = self.get_current_value('speaker')
        fc = self.get_current_value('fc')

        if speaker == 'primary':
            att = self.cal_primary.get_attenuation(fc, value)
            self.iface_behavior.set_tag('att1', att)
            self.iface_behavior.set_tag('att2', 120.0)
        elif speaker == 'secondary':
            att = self.cal_secondary.get_attenuation(fc, value)
            self.iface_behavior.set_tag('att2', att)
            self.iface_behavior.set_tag('att1', 120.0)
        else:
            raise ValueError, 'Unsupported speaker mode %r' % speaker

    def set_speaker_equalize(self, value):
        if value:
            firdata = self.cal_primary.fir_coefficients
            self.iface_behavior.set_coefficients('fir1', firdata)
        # Need to unset somehow?
