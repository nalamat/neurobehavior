from cns import equipment
from .aversive_controller import AversiveController
from enthought.traits.api import on_trait_change, Any
from enthought.pyface.api import error
from cns.pipeline import deinterleave
import numpy as np

import logging
log = logging.getLogger(__name__)

class AversiveControllerFM(AversiveController):

    contact_pipe = Any

    def _contact_pipe_default(self):
        targets = [self.model.data.optical_digital,
                   self.model.data.optical_digital_mean,
                   self.model.data.contact_digital,
                   self.model.data.contact_digital_mean,
                   self.model.data.trial_running, ]
        return deinterleave(targets)

    def init_equipment(self, info):
        self.pump = equipment.pump().Pump()
        self.backend = equipment.dsp()
        self.circuit = self.backend.load('aversive-behavior-FM', 'RX6')

    def configure_circuit(self, circuit, paradigm):
        if circuit is None:
            return
        elif circuit.running:
            raise SystemError, 'Cannot configure circuit while it is running'

        # This is an example of the "handler" approach.  The model
        # ('paradigm') does not have to concern itself about how the
        # equipment needs to be configured.  If we ever get a new set of
        # hardware, this code would be the only stuff that needs changing.
        circuit.reload()

        '''
        if paradigm.contact_method == 'touch':
            circuit.contact_method.value = 0
        else:
            circuit.contact_method.value = 1
        '''

        circuit.lick_th.value = paradigm.lick_th
        circuit.shock_n.set(0.3, src_unit='s')
        circuit.shock_delay_n.set(paradigm.shock_delay, src_unit='s')
        circuit.lick_nPer.set(paradigm.requested_lick_fs, 'fs')

        circuit.trial_buf.initialize(fs=circuit.fs)
        circuit.int_buf.initialize(fs=circuit.fs)
        circuit.int_buf.set(paradigm.signal_safe)

        circuit.contact_buf.initialize(channels=5, sf=127, src_type=np.int8,
                compression='decimated', fs=circuit.lick_nPer.get('fs'))

        #circuit.touch_buf.initialize(sf=3276, src_type=np.int16,
        #        compression='decimated', fs=circuit.lick_nPer.get('fs'))

        #circuit.optical_buf.initialize(sf=3276, src_type=np.int16,
        #        compression='decimated', fs=circuit.lick_nPer.get('fs'))

        circuit.pause_state.value = True
        self.backend.set_attenuation(paradigm.signal_safe.attenuation, 'PA5')

    def remind(self, info=None):
        print 'REMIND'
        self.state = 'manual'
        # The actual sequence is important.  We must finish uploading the signal
        # before we set the circuit flags to allow commencement of a trial.
        #self.circuit.trial_buf.set(self.current.signal_remind)
        self.circuit.depth.value = self.current.par_remind
        self.backend.set_attenuation(self.current.signal_remind.attenuation, 'PA5')
        self.circuit.shock_level.value = self.current.shock_remind
        self.circuit.pause_state.value = False # Everything's ready. GO!
        self.circuit.trigger(2)
        self.circuit.trigger(1)

    @on_trait_change('fast_tick')
    def task_update_data(self):
        data = self.circuit.contact_buf.read()
        self.contact_pipe.send(data)

    @on_trait_change('fast_tick')
    def task_monitor_circuit(self):
        if self.circuit.idx.value > self.current.idx:
            self.current.idx += 1
            ts = self.circuit.lick_ts_trial_start_n.value

            # Process "reminder" signals
            if self.state == 'manual':
                self.pause()
                self.model.data.update(ts,
                                       self.current.par_remind,
                                       self.current.shock_remind,
                                       'remind')
                #self.circuit.trial_buf.set(self.current.signal_warn)
                self.circuit.depth.value = self.current.par
                self.backend.set_attenuation(self.current.signal_warn.attenuation, 'PA5')
                self.circuit.shock_level.value = self.current.shock_level

            # Warning was just presented.
            else:
                last_trial = self.current.trial
                self.current.trial += 1     # reminders do not count
                # We are now looking at the current trial that will be presented.  
                # What do we need to do to get ready?
                
                if last_trial == self.current.safe_trials + 1:
                    log.debug('processing warning trial')
                    self.model.data.update(ts,
                                           self.current.par,
                                           self.current.shock_warn,
                                           'warn')
                    self.current.next()
                elif last_trial == self.current.safe_trials: 
                    self.model.data.update(ts, self.current.par, 0, 'safe')
                    #self.circuit.trial_buf.set(self.current.signal_warn)
                    self.circuit.depth.value = self.current.par
                    self.backend.set_attenuation(self.current.signal_warn.attenuation, 'PA5')
                    self.circuit.shock_level.value = self.current.shock_warn
                    self.circuit.trigger(2)
                elif last_trial < self.current.safe_trials:
                    self.model.data.update(ts, self.current.par, 0, 'safe')
                else:
                    raise SystemError, 'There is a mismatch.'
                    # TODO: Data has not been lost so we should not halt execution.
                    # However an appropriate warning should be sent.
                    
            # Signal to the circuit that data processing is done and it can commence execution
            self.circuit.trigger(1)
