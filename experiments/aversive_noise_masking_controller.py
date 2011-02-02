from numpy import random, zeros, concatenate

from tdt import DSPCircuit
from abstract_aversive_controller import AbstractAversiveController

class AversiveNoiseMaskingController(AbstractAversiveController):

    def init_equipment(self):
        # Handle to the circuit itself.  You need to provide the absolute or
        # relative path to the circuit itself.  If you launch the program from
        # the "root" directory (i.e. <path_to_neurobehavior> where components is
        # a subfolder) this will work.
        self.iface_behavior = DSPCircuit('components/aversive-behavior-masking', 'RZ6')

        # Handlers to the data buffers on the RZ6
        self.buffer_TTL = self.iface_behavior.get_buffer('TTL',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_contact = self.iface_behavior.get_buffer('contact',
                src_type='int8', dest_type='float32', block_size=24)

        # Handles to the trial and intertrial signal buffers on the RZ6
        self.buffer_trial = self.iface_behavior.get_buffer('trial')
        self.buffer_int = self.iface_behavior.get_buffer('int')

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
        repetitions = self.model.paradigm.repeats
        position = random.randint(1, 4)
        self.current_position = position
        par = self.current_warn.parameter
        shock_level = self.current_warn.shock_level
        # This is a list comprehension.  We are computing #repetition tokens and
        # have a list of that size.
        waveforms = [self.compute_waveform(par, position) for i in range(repetitions)]
        # Concatenate brings together those three (or whatever the nubmer is)
        # into a single waveform.
        waveform = concatenate(waveforms)
        # Buffer is a handle to the trial buffer on the RPvds.
        self.buffer_trial.set(waveform)

    def compute_waveform(self, parameter, position=0):
        fs = self.iface_behavior.fs

        # right now the variables are not protected.  If you change the value in
        # the GUI but don't hit Apply, the code will end up using the modified
        # value anyway.  The way to protect against this is to copy the
        # variables over during init_current to current_<variablename> and then
        # adding set_<variablename> = ExperimentController.reset_current to
        # allow the change to be applied when one hits "Apply".
        # I may add a feature that does this behind the scenes at some point
        # (i.e. you can call a variable a shadow variable and the controller
        # will recognize this and automatically copy it over).

        trial_duration = self.model.paradigm.trial_duration
        masker_duration = self.model.paradigm.masker_duration
        probe_duration = self.model.paradigm.probe_duration
        probe_amplitude = parameter

        # This assumes that the values entered in the GUI are reasonable.  NO
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
        repetitions = self.model.paradigm.repeats
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

            trial_duration = self.model.paradigm.trial_duration
            reps = self.model.paradigm.repeats

            total_duration = reps*trial_duration
            self.iface_behavior.cset_tag('trial_dur_n', total_duration, 's',
                    'n')
        else:
            ttype = 'safe'

        if ttype in ['warn', 'remind']:
            self.iface_behavior.set_tag('warn?', 1)
            reps = self.model.paradigm.repeats
        else:
            reps = random.randint(1, self.model.paradigm.repeats+1)
            self.iface_behavior.set_tag('warn?', 0)

        # Set duration of trial to trial_duration*number of repeats
        trial_duration = self.model.paradigm.trial_duration
        total_duration = trial_duration*reps
        self.iface_behavior.cset_tag('trial_dur_n', total_duration, 's', 'n')
        
        # cset_tag(tag, value, from_unit, to_unit) will convert the provided
        # value from from_unit to to_unit before setting the tag in the
        # circuit).  i.e. converting seconds to samples is basically
        # int(value*circuit.fs)

        # Fire a trigger when you've finished doing everything you need to
        # prepare for the next trial.
        self.iface_behavior.trigger(1)
