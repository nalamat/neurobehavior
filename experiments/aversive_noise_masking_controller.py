from numpy import random, zeros, concatenate
import os

from tdt import DSPCircuit
from abstract_aversive_controller import AbstractAversiveController

from cns.data.h5_utils import append_node, append_date_node, \
    get_or_append_node

import logging
log = logging.getLogger(__name__)
from aversive_data import RawAversiveData as AversiveData
from cns.pipeline import deinterleave_bits

from cns import RCX_ROOT

class AversiveNoiseMaskingController(AbstractAversiveController):
    # NOTE: Paradigms have access to all the classes (paradigm, data,
    # experiment, view) via self.model (experiment), self.model.paradigm,
    # self.model.data, and self.info.ui (view).

    # When the user hits the "Run" button, the paradigm is inspected.  If the
    # attribute has the metadata init=True, the set_<attribute name> method on
    # the controller is called with the value of the attribute.  Some set
    # methods need to change a hardware configuration (e.g. a tag value in the
    # RCX file, others simply need to store the current value in an attribute on
    # the controller.  Likewise, these methods are called when the user changes
    # a value via the GUI (when the experiment is running) and hits the apply
    # button.

    # At no point should your controller methods query the paradigm object
    # (available via self.model.paradigm) because the values may reflect changes
    # to the GUI that have not been applied yet.  If your controller needs a
    # certain value, store the current (i.e. most recently "applied" value) in
    # an attribute on the controller.  All of the set methods below follow this
    # strategy.

    def set_repeats(self, value):
        self.current_repeats = value

    def set_masker_duration(self, value):
        self.current_masker_duration = value

    def set_masker_amplitude(self, value):
        self.current_masker_amplitude = value

    def set_probe_duration(self, value):
        self.current_probe_duration = value

    def set_trial_duration(self, value):
        self.current_trial_duration = value

    def init_equipment(self):
        # Handle to the circuit itself.  You need to provide the absolute or
        # relative path to the circuit itself.  If you launch the program from
        # the "root" directory (i.e. <path_to_neurobehavior> where components is
        # a subfolder) this will work.
        circuit = os.path.join(RCX_ROOT, 'aversive-behavior-masking_RX6')
        self.iface_behavior = DSPCircuit(circuit, 'RX6')

        # Handlers to the data buffers on the RZ6
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL','r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact','r',
                src_type='int8', dest_type='float32', block_size=24)

        # Handles to the trial and intertrial signal buffers on the RZ6
        self.buffer_trial = self.iface_behavior.get_buffer('trial','w')
        self.buffer_int = self.iface_behavior.get_buffer('int','w')

    def update_safe(self):
        waveform = self.compute_waveform(self.current_safe.parameter,
                                         position=0)
        # set is a special method on DSPBuffer that uploads the entire waveform
        # to the buffer starting at index zero then "truncates" the buffer to
        # the length of the waveform by setting <buffername>_n tag.  The RPvds
        # system only allows you to set the buffer size smaller than the Size
        # specified in the circuit.  If you try to set it to a bigger size, you
        # will get an error.

        # Note that there is also another method called
        # self.buffer_int.write(waveform) which will track the last index
        # written to (so you can append data to the buffer rather than
        # overwriting the entire buffer).  This is used by the AM noise
        # paradigm to continuously update the noise token (see
        # AversiveController.update_safe()).
        self.buffer_int.set(waveform)

    def update_warn(self):
        # self.current_repeats is created by set_repeats, which is called when
        # the user starts the experiment (and also when the user makes a change
        # to the GUI)
        repetitions = self.current_repeats

        position = random.randint(1, 4)
        self.current_position = position

        # current_warn is set in abstract_aversive_paradigm in set_warn_sequence
        # (via reset_sequence) and also in tick_fast.
        par = self.current_warn.parameter
        shock_level = self.current_warn.shock_level

        # This is a list comprehension.  We are computing the token for each
        # repetition.  len(waveforms) will be equal to the number of
        # repetitions.
        waveforms = [self.compute_waveform(par, position) \
                     for i in range(repetitions)]

        # Equivalent approach to the above line
        # waveforms = []
        # for i in range(repetitions):
        #     waveform = self.compute_waveform(par, position)
        #     waveforms.append(waveform)

        # Concatenate brings together the list of waveforms into a single
        # waveform.
        waveform = concatenate(waveforms)

        # Buffer is a handle to the trial buffer on the RPvds
        self.buffer_trial.set(waveform)

    def compute_waveform(self, parameter, position=0):
        fs = self.iface_behavior.fs

        # Let's make local copies of the instance attributes (so the code is
        # more readable)
        trial_duration = self.current_trial_duration
        masker_duration = self.current_masker_duration
        probe_duration = self.current_probe_duration
        probe_amplitude = parameter

        # This assumes that the values entered in the GUI are reasonable.  No
        # error-checking is done.
        waveform = zeros(int(fs*trial_duration))
        masker = random.normal(size=int(fs*masker_duration))
        probe = random.normal(size=int(fs*probe_duration))*2

        # Everything below is the computation for the waveform.  Everything
        # above are the variables you need.
        masker_n = len(masker)
        probe_n = len(probe)

        waveform[probe_n:masker_n+probe_n] = masker
        if position == 0:
            return waveform # code will return here if called

        # If position is not 0, then we need to insert the probe
        if position == 1:
            offset = 0
        elif position == 2:
            offset = int(masker_n/2)
        elif position == 3:
            offset = masker_n+probe_n
        waveform[offset:offset+probe_n] += probe_amplitude*probe
        return waveform

    def update_remind(self):
        repetitions = self.current_repeats

        position = random.randint(1, 4)
        self.current_position = position
        par = self.current_remind.parameter
        # This is a list comprehension.  We are computing #repetition tokens and
        # have a list of that size.
        waveforms = [self.compute_waveform(par, position) for i in range(repetitions)]
        # Concatenate brings together those three (or whatever the nubmer is)
        # into a single waveform.
        waveform = concatenate(waveforms)
        # Buffer is a handle to the trial buffer on the RPvds.
        self.buffer_trial.set(waveform)

    def trigger_next(self):
        if self.state == 'manual':
            ttype = 'remind'
            self.iface_behavior.set_tag('warn?', 1)
        elif self.current_trial == self.current_num_safe + 1:
            ttype = 'warn'
            # Next trial is a warn trial
            self.iface_behavior.set_tag('warn?', 1)

            trial_duration = self.current_trial_duration
            reps = self.current_repeats
            total_duration = reps*trial_duration

            self.iface_behavior.cset_tag('trial_dur_n', total_duration, 's',
                                         'n')
        else:
            ttype = 'safe'

        if ttype in ['warn', 'remind']:
            self.iface_behavior.set_tag('warn?', 1)
            reps = self.current_repeats
        else:
            reps = random.randint(1, self.current_repeats+1)
            self.iface_behavior.set_tag('warn?', 0)

        # Set duration of trial to trial_duration*number of repeats
        trial_duration = self.current_trial_duration
        total_duration = trial_duration*reps
        self.iface_behavior.cset_tag('trial_dur_n', total_duration, 's', 'n')
        
        # cset_tag(tag, value, from_unit, to_unit) will convert the provided
        # value from from_unit to to_unit before setting the tag in the
        # circuit).  i.e. converting seconds to samples is basically
        # int(value*circuit.fs).  This is very similar to some functions in
        # Sharad's toolbox called ms2n

        # Fire a trigger when you've finished doing everything you need to
        # prepare for the next trial.
        self.iface_behavior.trigger(1)
