from __future__ import division

from os import path

from enthought.traits.api import Instance, File, List, Any, Int, Bool, Enum
from enthought.traits.ui.api import View, Include, VGroup

from experiments.evaluate import Expression

from time import time

# Contains some utility functions
from tdt.device import RZ6

import numpy as np

# __name__ is a special variable available to the module that will be
# "paradigms.positive_cmr" (i.e. the "name" of the module as seen by Python).
import logging
log = logging.getLogger(__name__)

from experiments.abstract_positive_experiment import AbstractPositiveExperiment
from experiments.abstract_positive_controller import AbstractPositiveController
from experiments.abstract_positive_paradigm import AbstractPositiveParadigm
from experiments.positive_data import PositiveData

from experiments.cl_experiment_mixin import CLExperimentMixin
from experiments.positive_cl_data_mixin import PositiveCLDataMixin

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin

class Controller(
        AbstractPositiveController, 
        PumpControllerMixin,
        ):
    '''
    Controls experiment logic (i.e. communicates with the TDT hardware,
    responds to input by the user, etc.).
    '''
    
    go_remind = List
    go_parameters = List   # Technically a list of lists
    nogo_parameters = List # Technically a list of lists
    
    random_generator = Any
    random_seed = Int
     
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
        node = info.object.data_node
        
        # We can set attributes on the node via the following syntax (there are
        # several ways to set attributes in Python including node.setAttr(...)
        # but I like this syntax.
        node._v_attrs['trial_sequence_random_seed'] = self.random_seed
        
        # Call the start_experiment method defined in
        # AbstractPositiveController.  We do this last because the
        # start_experiment method in AbstractPositiveController calls
        # trigger_next() so we need to make sure that the random number
        # generator is set up before the first trial is initialized.
        super(Controller, self).start_experiment(info)
   
    def set_hw_att(self, atten):
        # The RPvds circuit has a toggle to send the waveform to one speaker or
        # the other (the inactive speaker essentially recieves a string of 0's),
        # so we will simply set both speakers to the same attenuation to avoid
        # the "click" in between every trial that occurs when the hardware
        # attenuators are set.
        att_bits = RZ6.atten_to_bits(atten, atten)
        self.iface_behavior.set_tag('att_bits', att_bits)

    # set_nogo_filename and set_go_filename are only called when the value of
    # go_filename and nogo_filename change
    
    def set_nogo_filename(self, filename):
        log.debug("Loading nogo settings from {}".format(filename))

        # Use np.loadtxt instead of the csv module because it convers the data
        # to numeric values rather than loading as a string, then reverse the
        # array and convert it to a list.  We convert to a list because this
        # allows us to take advantage of the pop() method.  Numpy arrays do not
        # have this feature, so we'd have to rewrite other parts of the code if
        # we kept the data structure as an array rather than converting it to a
        # list.
        self.nogo_parameters = np.loadtxt(filename, delimiter=',')[::-1].tolist()

    def set_go_filename(self, filename):
        log.debug("Loading go settings from {}".format(filename))
        go_parameters = np.loadtxt(filename, delimiter=',')[::-1].tolist()
        
        # The first line of the CSV file (now the last element of the list
        # since we've reversed it) defines the settings for the GO_REMIND.
        self.go_remind = go_parameters.pop()
        
        # pop() removes the element of the list, so we are now left with all
        # but the first line of the CSV file.
        self.go_parameters = go_parameters

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
        speaker = self.get_current_value('speaker')
        hw_att = self.get_current_value('hw_att')
        go_probability = self.get_current_value('go_probability')
        
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
        
        masker_file = r'E:\programs\ANTJE CMR\CMR\stimuli\M{}{}{}{}.stim'.format(int(F), int(E), int(FC), int(TokenNo))
        target_file = r'E:\programs\ANTJE CMR\CMR\stimuli\T{}{}.stim'.format(int(FC), int(TargetNo))
        
        masker = np.fromfile(masker_file, dtype=np.float32)
        target = np.fromfile(target_file, dtype=np.float32)

        # This method will return the theoretical SPL of the speaker assuming
        # you are playing a tone at the specified frequency and voltage (i.e.
        # Vrms)
        dBSPL_RMS1 = cal.get_spl(frequencies=1e3, voltage=1)

        # Scale waveforms so that we get desired stimulus level assuming 0 dB of
        # attenuation
        masker = 10**((ML-dBSPL_RMS1)/20)*masker
        target = 10**((TL-dBSPL_RMS1)/20)*target
        stimulus = target + masker     
        
        stimulus = stimulus * 10**(hw_att/20)

        # Set the flag in the RPvds circuit that indicates which output to send
        # the waveform to
        if speaker == 'primary':
            self.iface_behavior.set_tag('speaker', 0)
        elif speaker == 'secondary':
            self.iface_behavior.set_tag('speaker', 1)

        self.buffer_out.set(stimulus)
    
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
        self.set_current_value('masker_level',ML)
        self.set_current_value('TMR',TL-ML)
        self.set_current_value('target_number',TargetNo)
        self.set_current_value('masker_number',TokenNo)
        self.set_current_value('masker_envelope',E)
        self.set_current_value('masker_flanker',F)
        self.set_current_value('center_frequency',FC)

        # This is a "handshake" that lets the RPvds circuit know that we are
        # done with preparations for the next trial (e.g. uploading the stimulus
        # waveform).  The RPvds circuit will not proceed with the next trial
        # until it receives a "SoftTrig1" (in TDT parlance)
        self.iface_behavior.trigger(1)

    def log_trial(self, **kwargs):
        # HDF5 data files do not natively support unicode strings so we need to
        # convert our filename to an ASCII string.  While we're at it, we should
        # probably strip the directory path as well and just save the basename.
        go_filename = self.get_current_value('go_filename')
        kwargs['go_filename'] = str(path.basename(go_filename))
        nogo_filename = self.get_current_value('nogo_filename')
        kwargs['nogo_filename'] = str(path.basename(nogo_filename))
        super(Controller, self).log_trial(**kwargs)
    
class Paradigm(
        AbstractPositiveParadigm, 
        PumpParadigmMixin,
        ):
    '''
    Defines the parameters required by the experiment (e.g. duration of various
    events, frequency of the stimulus, which speaker is active, etc.).
    '''
    
    go_probability = Expression('0.5 if c_nogo < 5 else 1', 
            label='Go probability', log=False, context=True)
    repeat_fa = Bool(True, label='Repeat if FA?', log=True, context=True)
    nogo_filename = File(context=True, log=False, label='NOGO filename')
    go_filename = File(context=True, log=False, label='GO filename')

    target_level = Int(label='Target Level', log=True, context=True)
    masker_level = Int(label='Masker Level', log=True, context=True)
    TMR = Int(label='Target Level', log=True, context=True)
    target_number = Int(label='Target Token Number', log=True, context=True)
    masker_number = Int(label='Masker Token Number', log=True, context=True)
    masker_envelope = Int(label='Masker Envelope', log=True, context=True)
    masker_flanker = Int(label='Masker with or without Flanker', log=True, context=True)
    center_frequency = Int(label='Masker with or without Flanker', log=True, context=True)
    
    hw_att = Enum(0, 20, 40, 60, context=True, log=True, label='HW attenuation (dB)')
    
    traits_view = View(
            VGroup(
                'go_probability',
                Include('abstract_positive_paradigm_group'),
                Include('pump_paradigm_mixin_syringe_group'),
                label='Paradigm',
                ),
            VGroup(
                Include('speaker_group'),
                'hw_att',
                'nogo_filename',
                'go_filename',
                label='Sound',
                ),
            )

class Data(PositiveData, PositiveCLDataMixin, PumpDataMixin):
    '''
    Container for the data
    '''

class Experiment(AbstractPositiveExperiment, CLExperimentMixin):
    '''
    Defines the GUI layout
    '''

    data = Instance(Data, (), store='child')
    paradigm = Instance(Paradigm, (), store='child')

node_name = 'PositiveCMRExperiment'
