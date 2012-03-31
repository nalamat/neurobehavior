from __future__ import division

from os import path

import numpy as np

from cns.pipeline import deinterleave_bits

from enthought.traits.api import Instance, File, List, Any, Int, Bool, Enum, Button
from enthought.traits.ui.api import (View, Include, VSplit, VGroup, Item,
        HSplit, HGroup, Tabbed, ShellEditor)

# These mixins are shared with the positive_cmr paradigm.  I use the underscore
# so it's clear that these files do not define stand-alone paradigms.
from ._positive_cmr_mixin import PositiveCMRParadigmMixin
from ._positive_cmr_mixin import PositiveCMRControllerMixin

from experiments.positive_stage1_data import PositiveStage1Data
from experiments.positive_stage1_controller import PositiveStage1Controller
from experiments.positive_stage1_experiment import PositiveStage1Experiment
from experiments.positive_stage1_paradigm import PositiveStage1Paradigm

from experiments.pump_controller_mixin import PumpControllerMixin
from experiments.pump_paradigm_mixin import PumpParadigmMixin
from experiments.pump_data_mixin import PumpDataMixin


from cns import get_config

import logging
log = logging.getLogger(__name__)

class Controller(
        PositiveCMRControllerMixin,
        PositiveStage1Controller,
        PumpControllerMixin,
        ):
    
    cycle = Button

    def setup_experiment(self, info):
        filename = 'positive-behavior-training-contmask-v4'
        circuit = path.join(get_config('RCX_ROOT'), filename)
        self.iface_behavior = self.process.load_circuit(circuit, 'RZ6')
        self.buffer_masker = self.iface_behavior.get_buffer('masker', 'w')
        self.buffer_target = self.iface_behavior.get_buffer('target', 'w')

        self.buffer_TTL = self.iface_behavior.get_buffer('TTL', 'r',
                block_size=24, src_type='int8', dest_type='int8')
        self.buffer_mic = self.iface_behavior.get_buffer('mic', 'r')
        self.model.data.spout_TTL.fs = self.buffer_TTL.fs
        self.model.data.override_TTL.fs = self.buffer_TTL.fs
        self.model.data.pump_TTL.fs = self.buffer_TTL.fs
        self.model.data.signal_TTL.fs = self.buffer_TTL.fs
        self.model.data.free_run_TTL.fs = self.buffer_TTL.fs
        self.model.data.microphone.fs = self.buffer_mic.fs

        targets = [self.model.data.spout_TTL,
                   self.model.data.override_TTL,
                   self.model.data.pump_TTL, 
                   self.model.data.signal_TTL,
                   self.model.data.free_run_TTL ]
        self.pipeline_TTL = deinterleave_bits(targets)

        self.iface_pump.set_trigger(start='rising', stop='falling')
        self.iface_pump.set_direction('infuse')
        self.iface_pump.set_volume(0)

    def start_experiment(self, info):
        # AbstractExperimentController defines a method, start(), that is called
        # whenever the user presses the button named start in the toolbar.
        # start() performs some initialization (e.g. setup_experiment() then
        # start_experiment()).

        # Now, we need to initialize the masker buffer here before the zBUS A
        # trigger is set to high.  Simply calling
        # get_current_value('masker_filename') should cause the
        # set_masker_filename() method to be called right away.
        self.invalidate_context()
        self.get_current_value('masker_filename')
        super(Controller, self).start_experiment(info)
    
    # This gets called when someone presses the "cycle" button (or,
    # alternatively, does self.button = somevalue).  This is a feature of
    # Enthought's Traits package (e.g. when you define a button on a class that
    # inherits from HasTraits), then everytime the button is pressed,
    # Enthought's Traits system will call a method _button_fired (where button
    # is the name of the button attribute).
    def _cycle_fired(self):
        log.debug('Cycle button pressed')
        self.update_signal()

    def set_hw_att(self, hw_atten):
        # Update the hardware attenuators.  Set att_B to 120 since we only use
        # the primary output by default.
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            self.iface_behavior.set_tag('att_A', hw_atten)
            self.iface_behavior.set_tag('att_B', 120)
        else:
            self.iface_behavior.set_tag('att_A', 120)
            self.iface_behavior.set_tag('att_B', hw_atten)

        log.debug('Updated hardware attenuators')

        # The masker scaling factor depends on the hardware attenuation value,
        # so we need to be sure to configure that as well.
        self._update_masker_sf()
        
    def update_waveform(self):
        # Force a recomputation of all variables by clearing the cached values
        self.invalidate_context()

        # Now, do the actual recomputation of all variables, calling
        # set_variable_name as needed.
        self.evaluate_pending_expressions()

        # Now, upload the waveform.
        log.debug('uploading new target to the RPvds circuit')

        hw_att = self.get_current_value('hw_att')
        calibration = self.cal_primary
        settings = self.go_parameters.pop()
        F, E, FC, ML, TL, TokenNo, TargetNo = settings

        # Eventually you'll probably want to move these to cns.settings that way
        # you can override it on a per-computer basis via the local-settings.py
        # file that's referenced by NEUROBEHAVIOR_SETTINGS
        target_directory = r'C:\Experimental_Software\sounds\CMR\stimuli'
        target_filename = 'T{}{}.stim'.format(int(FC), int(TargetNo))
        target_file = path.join(target_directory, target_filename)
        target = np.fromfile(target_file, dtype=np.float32)

        # This method will return the theoretical SPL of the speaker assuming
        # you are playing a tone at the specified frequency and voltage (i.e.
        # Vrms)
        dBSPL_RMS1 = calibration.get_spl(frequencies=1e3, voltage=1)

        # Scale waveforms so that we get desired stimulus level assuming 0 dB of
        # attenuation
        target = 10**((TL-dBSPL_RMS1)/20)*target
        target = target * 10**(hw_att/20)
        self.buffer_target.set(target)
    
        self.set_current_value('target_level', TL)
        #self.set_current_value('masker_level',ML)
        ML = self.get_current_value('masker_level')
        self.set_current_value('TMR',TL-ML)
        self.set_current_value('target_number',TargetNo)
        self.set_current_value('center_frequency',FC)

class Paradigm(
        PositiveCMRParadigmMixin,
        PositiveStage1Paradigm, 
        PumpParadigmMixin,
        ):

    traits_view = View(
            VGroup(
                Include('signal_group'),
                'speaker',
                'hw_att',
                'go_filename',
                'masker_filename',
                'masker_level',
                label='Sound',
                ),
            )

class Data(PositiveStage1Data, PumpDataMixin): pass

class Experiment(PositiveStage1Experiment):

    data = Instance(Data, ())
    paradigm = Instance(Paradigm, ())

node_name = 'CMRTraining'
