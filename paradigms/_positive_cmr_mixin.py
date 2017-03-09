from traits.api import HasTraits, File, Int, Enum, Any, List, Float, Expression
import numpy as np
from os import path
import time

import logging
log = logging.getLogger(__name__)

class PositiveCMRParadigmMixin(HasTraits):

    kw = {'context': True, 'log': True}

    masker_filename  = File('CMR/supermasker4.wav', label='Masker filename'            , **kw)
    masker_level     = Expression(0               , label='Masker attenuation (dB)'    , **kw)
    masker_frequency = Expression(10              , label='Masker frequency (Hz)'      , **kw)
    target_filename  = File('CMR/T01.wav'         , label='Target filename'            , **kw)
    target_level     = Expression(0               , label='Target attenuation (dB)'    , **kw)
    TMR              = Int(                         label='Target level'               , **kw)
    target_number    = Int(                         label='Target token number'        , **kw)
    center_frequency = Int(                         label='Masker with/without flanker', **kw)
    hw_att           = Enum(0, 20, 40, 60         , label='HW attenuation (dB)'        , **kw)


class PositiveCMRControllerMixin(HasTraits):

    go_remind = List
    go_parameters = List   # Technically a list of lists
    nogo_parameters = List # Technically a list of lists

    masker_memmap = Any
    masker_index = Any

    # Update the value stored in current_context immediately rather than having
    # the user hit the "apply" button.
    current_masker_sf = Float(0, context=True, log=True, immediate=True,
                              label='Masker scaling factor')

    def set_masker_filename(self, filename):
        print 'setting', filename
        if not path.exists(filename):
            raise ValueError, 'Masker file {} does not exist'.format(filename)
        log.debug("Configuring masker from {}".format(filename))
        self.masker_memmap = np.memmap(filename, np.float32, 'r')
        self.masker_index = 0 # This will track the last uploaded index in the
                              # masker file
        self.update_masker()

    def set_masker_level(self, level):
        self._update_masker_sf()

    def _update_masker_sf(self):
        speaker = self.get_current_value('speaker')
        if speaker == 'primary':
            calibration = self.cal_primary
        else:
            calibration = self.cal_secondary

        hw_att = self.get_current_value('hw_att')
        level = self.get_current_value('masker_level')

        dBSPL_RMS1 = calibration.get_spl(frequencies=1e3, voltage=1)-hw_att
        old_sf = self.current_masker_sf
        new_sf = 10.0**((level-dBSPL_RMS1)/20.0)
        self.current_masker_sf = new_sf
        ramp = np.cos(np.linspace(0, np.pi/2.0, 50))**2
        ramp_sf = (old_sf-new_sf)*ramp+new_sf

        # I'm not exactly sure what the most accurate way to time code execution
        # is.  There are blogs online about this, but this is fine for now.
        log.debug('ramping masker sf from %f to %f', old_sf, new_sf)
        tick = time.time()
        for sf in ramp_sf:
            # We are relying on the fact that the method below will take ~21.4
            # usec to execute.  This means that the ramp will be ~1ms.  This is
            # not guaranteed though.
            self.iface_behavior.set_tag('masker_scale', sf)
        log.debug('ramp took %f usec to complete', (time.time()-tick)*1e6)

    # set_nogo_filename and set_go_filename are only called when the value of
    # go_filename and nogo_filename change

    # Even though the positive CMR training controller doesn't have a nogo
    # filename, it's OK to have it here.
    def set_nogo_filename(self, filename):
        if not path.exists(filename):
            raise ValueError, 'NOGO file {} does not exist'.format(filename)
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
        if not path.exists(filename):
            raise ValueError, 'GO file {} does not exist'.format(filename)
        log.debug("Loading go settings from {}".format(filename))
        go_parameters = np.loadtxt(filename, delimiter=',')[::-1].tolist()

        # The first line of the CSV file (now the last element of the list
        # since we've reversed it) defines the settings for the GO_REMIND.
        self.go_remind = go_parameters.pop()

        # pop() removes the element of the list, so we are now left with all
        # but the first line of the CSV file.
        self.go_parameters = go_parameters

    def update_masker(self):
        # Get the correct calibration file
        #speaker = self.get_current_value('speaker')
        #if speaker == 'primary':
        #    cal = self.cal_primary
        #else:
        #    cal = self.cal_secondary

        # Check to see how much data can be uploaded to the masker buffer right
        # now and do so
        samples = self.buffer_masker.available()
        log.debug('%d samples need to be written to the buffer', samples)

        #dBSPL_RMS1 = cal.get_spl(frequencies=1e3, voltage=1)
        #masker_level = self.get_current_value('masker_level')

        # Check if we need to wrap around to the beginning of the masker file
        if (samples + self.masker_index) > len(self.masker_memmap):
            log.debug('Near end of masker file.  Splitting into two reads.')
            # Write the last few samples remaining from the end of the masker
            # file
            masker = self.masker_memmap[self.masker_index:]
            #masker = 10**((masker_level-dBSPL_RMS1)/20)*masker
            self.buffer_masker.write(masker)
            log.debug('Uploaded %d samples to the masker', len(masker))
            #log.debug('Vrms of uploaded waveform is %f', np.mean(masker**2)**0.5)

            # Reset the pointer to the beginning of the masker file and update
            # the number of remaining samples to be written
            self.masker_index = 0
            samples -= len(masker)
            log.debug('%%%%% Wrapping around to beginning of masker file')

        masker = self.masker_memmap[self.masker_index:self.masker_index+samples]
        #masker = 10**((masker_level-dBSPL_RMS1)/20)*masker
        log.debug('Uploaded %d samples to the masker', samples)
        #log.debug('Vrms of uploaded waveform is %f', np.mean(masker**2)**0.5)

        self.buffer_masker.write(masker)
        self.masker_index = self.masker_index + samples
        log.debug('Masker index is now %d', self.masker_index)
