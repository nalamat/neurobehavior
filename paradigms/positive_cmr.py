'''
Appetitive comodulation masking release (continuous noise)
----------------------------------------------------------
:Author: **Brad Buran <bburan@alum.mit.edu>**
:Author: **Antje Ihlefeld <ai33@nyu.edu>**
:Method: Constant limits go-nogo
:Status: Alpha.  Currently under development and testing.

    param1 : unit
        description
    param2 : unit
        description

This paradigm differs slightly from positive_dt_cl and positive_am_noise_cl in
several key respects::

    * The sequence of go/nogo tokens are defined by a csv (comma separated
      values)

    * The target is added to a continuous masker

    * Both the target and masker waveforms are pre-computed using a Matlab
      script and saved to a float32 binary file.

'''

from __future__ import division

from os import path

from enthought.traits.api import Instance, File, Any, Int, Bool
from enthought.traits.ui.api import View, Include, VGroup

from experiments.evaluate import Expression

from cns import get_config
from cns.pipeline import deinterleave_bits

from tdt.device import RZ6
from time import time

# These mixins are shared with the positive_cmr_training paradigm.  I use the
# underscore so it's clear that these files do not define stand-alone paradigms.
from ._positive_cmr_mixin import PositiveCMRParadigmMixin
from ._positive_cmr_mixin import PositiveCMRControllerMixin

import numpy as np

# __name__ is a special variable available to the module that will be
# "paradigms.positive_cmr" (i.e. the "name" of the module as seen by Python).
import logging
log = logging.getLogger(__name__)

from experiments.abstract_positive_experiment_v3 import AbstractPositiveExperiment
from experiments.abstract_positive_controller_v3 import AbstractPositiveController
from experiments.abstract_positive_paradigm_v3 import AbstractPositiveParadigm
from experiments.positive_data_v3 import PositiveData
from experiments.positive_cl_data_mixin import PositiveCLDataMixin
from experiments.cl_experiment_mixin import CLExperimentMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        PositiveCMRControllerMixin,
        AbstractPositiveController, 
        PumpControllerMixin,
        ):
    '''
    Controls experiment logic (i.e. communicates with the TDT hardware,
    responds to input by the user, etc.).
    '''
    
    random_generator = Any
    random_seed = Int

    def setup_experiment(self, info):
        circuit = path.join(get_config('RCX_ROOT'), 'positive-behavior-contmask-v4')
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')

        self.buffer_target = self.iface_behavior.get_buffer('target', 'w')
        self.buffer_masker = self.iface_behavior.get_buffer('masker', 'w')

        self.buffer_TTL1 = self.iface_behavior.get_buffer('TTL', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_TTL2 = self.iface_behavior.get_buffer('TTL2', 'r',
                src_type='int8', dest_type='int8', block_size=24)
        self.buffer_poke_start = self.iface_behavior.get_buffer('poke_all/',
                'r', src_type='int32', dest_type='int32', block_size=1)
        self.buffer_poke_end = self.iface_behavior.get_buffer('poke_all\\', 'r',
                src_type='int32', dest_type='int32', block_size=1)

        # microphone
        self.buffer_mic = self.iface_behavior.get_buffer('mic', 'r')
        self.model.data.microphone.fs = self.buffer_mic.fs

        self.fs_conversion = self.iface_behavior.get_tag('TTL_d')

        # Stored in TTL1
        self.model.data.spout_TTL.fs = self.buffer_TTL1.fs
        self.model.data.poke_TTL.fs = self.buffer_TTL1.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL1.fs
        self.model.data.reaction_TTL.fs = self.buffer_TTL1.fs
        self.model.data.response_TTL.fs = self.buffer_TTL1.fs
        self.model.data.reward_TTL.fs = self.buffer_TTL1.fs

        # Stored in TTL2
        self.model.data.TO_TTL.fs = self.buffer_TTL2.fs

        # Timestamp data
        self.model.data.trial_epoch.fs = self.iface_behavior.fs
        self.model.data.signal_epoch.fs = self.iface_behavior.fs
        self.model.data.poke_epoch.fs = self.iface_behavior.fs
        self.model.data.all_poke_epoch.fs = self.iface_behavior.fs
        self.model.data.response_ts.fs = self.iface_behavior.fs

        targets1 = [self.model.data.poke_TTL, self.model.data.spout_TTL,
                    self.model.data.reaction_TTL, self.model.data.signal_TTL,
                    self.model.data.response_TTL, self.model.data.reward_TTL, ]

        # If the target is set to None, this means that we aren't interested in
        # capturing the value of that specific bit.  Nothing is stored in the
        # first bit of the TTL_2 data; however, we store the timeout TTL in the
        # second bit.
        targets2 = [None, self.model.data.TO_TTL]

        # deinterleave_bits is the Python complement of the RPvds FromBits
        # component that breaks down the integer into its individual bits.
        # Targets are the destination channel (which map to the underlying HDF5
        # array) for each bit.  e.g. the value of the first bit gets sent to
        # targets1[0] (which is the poke_TTL).  deinterleave_bits is a
        # "pipeline" function that automatically performs its function each time
        # new data arrives and hands the result off to the targets.  The targets
        # recieve this data and store it in the HDF5 array and notify the GUI
        # that new data has arrived and should be plotted.
        self.pipeline_TTL1 = deinterleave_bits(targets1)
        self.pipeline_TTL2 = deinterleave_bits(targets2)

        # Configure the pump
        self.iface_pump.set_trigger(start='rising', stop=None)
        self.iface_pump.set_direction('infuse')
     
    def start_experiment(self, info):    
        # When the user hits the start button,
        # AbstractExperimentController.start() is called.  This method then
        # calls start_experiment() which is defined here.  Note that at the very
        # end of this method, we call
        # AbstractPositiveExperiment.start_experiment() to finish the sequence
        # of operations that are required to run the experiment.

        # Generate a random seed based on the computer's clock.
        self.random_seed = int(time())
        
        # If we were to call any of the numpy.random functions (e.g.
        # numpy.random.uniform) directly, they would use a shared seed.  This is
        # problematic because if other parts of the program (e.g.e the noise
        # generator) were to call the random function directly, it would affect
        # the random sequence as well.  By creating a "randomstate" object, we
        # can be assured that no other part of the code will affect this
        # particular random number sequence.
        self.random_generator = np.random.RandomState(self.random_seed)
        
        # Now, save the random seed to our data node so we can recover it later.
        # info.object.data_node is a reference to the
        # ../PositiveCMRExperiment_YYYY_MM_DD_HH_MM_SS node in the HDF5 file.
        node = info.object.experiment_node
        
        # We can set attributes on the node via the following syntax (there are
        # several ways to set attributes in Python including node.setAttr(...)
        # but I like this syntax.
        node._v_attrs['trial_sequence_random_seed'] = self.random_seed

        self.refresh_context()

        # Now, we need to initialize the masker buffer here before the zBUS A
        # trigger is set to high.  Simply calling
        # get_current_value('masker_filename') should cause the
        # set_masker_filename() method to be called right away.
        masker_filename = self.get_current_value('masker_filename')
        
        # Call the start_experiment method defined in
        # AbstractPositiveController.  We do this last because the
        # start_experiment method in AbstractPositiveController calls
        # trigger_next() so we need to make sure that the random number
        # generator is set up before the first trial is initialized.
        super(Controller, self).start_experiment(info)

    # The positive training paradigms use the AudioOut macro, which requires the
    # value in dB attenuation for each output.  However, due to hardware
    # limitations, the attenuation is configured differently for the actual
    # positive paradigms.  Therefore, we cannot "share" the set_hw_att method
    # between the two.
    def set_hw_att(self, atten):
        # The RPvds circuit has a toggle to send the waveform to one speaker or
        # the other (the inactive speaker essentially recieves a string of 0's),
        # so we will simply set both speakers to the same attenuation to avoid
        # the "click" in between every trial that occurs when the hardware
        # attenuators are set.
        att_bits = RZ6.atten_to_bits(atten, atten)
        self.iface_behavior.set_tag('att_bits', att_bits)
        self._update_masker_sf()
   
    def trigger_next(self):
        # This function is *required* to be called.  This basically calls the
        # logic (defined in AbstractExperimentController) which clears the
        # current value of all parameters and recomputes them (this is important
        # in between trials).
        self.invalidate_context()

        # This must be called before the start of every trial to load (or
        # evaluate if the parameter is an expression) the values of each
        # parameter.  Note this method will also check to see if the value of a
        # parameter has changed since the last trial.  If so, the corresponding
        # set_parametername method will be called with the new value as an
        # argument.
        self.evaluate_pending_expressions()

        # For all variables declared as context=True, you can get the current
        # value via self.get_current_value().  This gives the
        # abstract_experiment_controller a chance to compute the values of any
        # parameters that are defined by expressions first.
        repeat_fa = self.get_current_value('repeat_fa')
        hw_att = self.get_current_value('hw_att')
        go_probability = self.get_current_value('go_probability')
        
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            cal = self.cal_primary
        else:
            cal = self.cal_secondary
        
        # Determine whether the animal false alarmed by checking the spout and
        # nogo data.  The last value in the "self.model.data.yes_seq" (which is
        # a list) will be True if he went to the spout.  The last value in
        # self.model.data.nogo_seq will be True if it was a NOGO or NOGO_REPEAT
        # trial.
        try:
            spout = self.model.data.yes_seq[-1]
            nogo = self.model.data.nogo_seq[-1]
        except IndexError:
            spout = False
            nogo = False

        # First, decide if it's a GO, GO_REMIND, NOGO or NOGO_REPEAT
    
        if len(self.model.data.trial_log) == 0:
            # This is the very first trial
            ttype = 'GO_REMIND'
            settings = self.go_remind
        elif self.remind_requested:
            # When the user clicks on the "remind" button, it sets the
            # remind_requested attribute on the experiment controller to True.
            ttype = 'GO_REMIND'
            settings = self.go_remind
        elif nogo and spout and repeat_fa:
            # The animal false alarmed and the user wishes to repeat the trial
            # if the animal false alarms
            ttype = 'NOGO_REPEAT'
            settings = self.nogo_parameters.pop()
        elif self.random_generator.uniform() < go_probability:
            ttype = 'GO'
            settings = self.go_parameters.pop()
        else:
            ttype = 'NOGO'
            settings = self.nogo_parameters.pop()
            
        # Each time we pop() a parameter, it is removed from the list and
        # returned
        
        # "unpack" our list into individual variables
        F, E, FC, ML, TL, TokenNo, TargetNo = settings
        
        #masker_file = r'E:\programs\ANTJE CMR\CMR\stimuli\M{}{}{}{}.stim'.format(int(F), int(E), int(FC), int(TokenNo))
        target_file = r'C:\Experimental_Software\sounds\CMR\stimuli\T{}{}.stim'.format(int(FC), int(TargetNo))
        
        #masker = np.fromfile(masker_file, dtype=np.float32)
        target = np.fromfile(target_file, dtype=np.float32)

        # This method will return the theoretical SPL of the speaker assuming
        # you are playing a tone at the specified frequency and voltage (i.e.
        # Vrms)
        dBSPL_RMS1 = cal.get_spl(frequencies=1e3, voltage=1)

        # Scale waveforms so that we get desired stimulus level assuming 0 dB of
        # attenuation
        #masker = 10**((ML-dBSPL_RMS1)/20)*masker
        target = 10**((TL-dBSPL_RMS1)/20)*target
        #stimulus = target + masker     
        stimulus = target
        
        stimulus = stimulus * 10**(hw_att/20)

        # Set the flag in the RPvds circuit that indicates which output to send
        # the waveform to
        if speaker == 'primary':
            self.iface_behavior.set_tag('speaker', 0)
        elif speaker == 'secondary':
            self.iface_behavior.set_tag('speaker', 1)

        self.buffer_target.set(stimulus)
    
        # Be sure that the trial type is added to the list of context variables
        # that will be saved to the trial_log file.
        self.set_current_value('ttype', ttype)

        # Boolean flag in the circuit that indicates whether or not the current
        # trial is a go.  This ensures that a reward is not delivered on NOGO
        # trials.
        if ttype.startswith('GO'):
            self.iface_behavior.set_tag('go?', 1)
        else:
            self.iface_behavior.set_tag('go?', 0)
        
        self.set_current_value('target_level', TL)
        #self.set_current_value('masker_level',ML)
        #self.set_current_value('masker_level',ML)
        ML = self.get_current_value('masker_level')
        self.set_current_value('TMR',TL-ML)
        self.set_current_value('target_number',TargetNo)
        #self.set_current_value('masker_number',TokenNo)
        #self.set_current_value('masker_envelope',E)
        #self.set_current_value('masker_flanker',F)
        self.set_current_value('center_frequency',FC)

        # This is a "handshake" that lets the RPvds circuit know that we are
        # done with preparations for the next trial (e.g. uploading the stimulus
        # waveform).  The RPvds circuit will not proceed with the next trial
        # until it receives a "SoftTrig1" (in TDT parlance)
        log.debug('Sending the trial-ready trigger to the RPvds circuit') 
        self.iface_behavior.trigger(1)

    # The training program does not log any trial information (we really don't
    # have the concept of a "trial" in the training program)
    def log_trial(self, **kwargs):
        # HDF5 data files do not natively support unicode strings so we need to
        # convert our filename to an ASCII string.  While we're at it, we should
        # probably strip the directory path as well and just save the basename.
        go_filename = self.get_current_value('go_filename')
        kwargs['go_filename'] = str(path.basename(go_filename))
        nogo_filename = self.get_current_value('nogo_filename')
        kwargs['nogo_filename'] = str(path.basename(nogo_filename))
        masker_filename = self.get_current_value('masker_filename')
        kwargs['masker_filename'] = str(path.basename(masker_filename))
        super(Controller, self).log_trial(**kwargs)

    def monitor_behavior(self):
        self.update_masker()
        # Run the rest of the "monitor_behavior" logic defined in
        # AbstractPositiveController
        super(Controller, self).monitor_behavior()
    
class Paradigm(
        PositiveCMRParadigmMixin,
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        ):
    '''
    Defines the parameters required by the experiment (e.g. duration of various
    events, frequency of the stimulus, which speaker is active, etc.).
    '''

    # Parameters specific to the actual appetitive paradigm that are not needed
    # by the training program (and therefore not in the "mixin")
    go_probability = Expression('0.5 if c_nogo < 5 else 1', 
            label='Go probability', log=False, context=True)
    repeat_fa = Bool(True, label='Repeat if FA?', log=True, context=True)

    nogo_filename = File(context=True, log=False, label='NOGO filename')
    go_filename = File(context=True, log=False, label='GO filename')
    
    traits_view = View(
            VGroup(
                'go_probability',
                Include('abstract_positive_paradigm_group'),
                Include('pump_paradigm_mixin_syringe_group'),
                label='Paradigm',
                ),
            VGroup(
                # Note that because the Paradigm class inherits from
                # PositiveCMRParadigmMixin all the parameters defined there are
                # available as if they were defined on this class.
                Include('speaker_group'),
                'hw_att',
                'nogo_filename',
                'go_filename',
                'masker_filename',
                'masker_level',
                label='Sound',
                ),
            )

class Data(PositiveData, PositiveCLDataMixin, PumpDataMixin):
    '''
    Container for the data
    '''
    pass

class Experiment(AbstractPositiveExperiment, CLExperimentMixin):
    '''
    Defines the GUI layout
    '''

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'PositiveCMRExperiment'
