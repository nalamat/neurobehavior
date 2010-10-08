"""
This will hopefully be replaced by the new system that is developed by our
programmer.  For now, this is just quick and dirty documentation to get started.
I'm not a fan of how I implemented this, and won't be upset to see it replaced
by a better, more streamlined system (that can handle calibration, etc).

Simply put, if you want to be able to define your own signals, you need to
create a subclass of this.

If you want
class Equipment(HasTraits): fs = Float(store='attribute', configurable=False,
label='Sampling frequency', unit='Hz') attenuation = Float(store='attribute',
log_changes=True, configurable=True, unit='dB')

Basically the code attaches two properties to class Equipment using Traits.  We
can then "inspect" the property to find out the information we need.  The
auto-generation of the GUI that allows us to configure the properties for this
class would look for a "label" metadata and use that label instead of the
property name if available.  This gives us a GUI:

Sampling frequency: [ enter value here ] Attenuation: [ enter value here ]

I wrote a modified version of the GUI creation code to factor in additional
metadata (specifically "configurable" and "unit").  The modified GUI creation
code will create a GUI that looks like:

Sampling frequency (Hz): 100,000 Hz <= not configurable so we don't provide a
field for the user to enter data Attenuation (dB): [enter value here]

"""
from cns.signal.view_factory import signal_view_factory
from cns.buffer import BlockBuffer
from enthought.traits.api import HasTraits, Str, Property, Float, CFloat, Range, \
    Array, List, Int
from enthought.traits.ui.api import EnumEditor, Handler, View
from enthought.savage.traits.ui.svg_button import SVGButton
from cns.widgets import icons
from cns.signal.calibration import DummyCalibration
import numpy as np
import logging
log = logging.getLogger(__name__)

# I have added new metadata properties to the trait definitions in this
# file:
#   unit - The unit the trait takes (i.e. Hz, sec, kHz).  Eventually we could
#   write a unit conversion class that returns the apporpriate value.
#   configurable - Means the parameter can be configured

class Waveform(HasTraits, BlockBuffer):
    '''Orphaned class'''

    fs = CFloat(100, store='attribute')
    signal = Property(Array(dtype='f'))
    t = Property(depends_on='fs, signal')

    blocks = 2 # Needed to implement the BlockBuffer reads

class Signal(Waveform):

    coerced_duration = Property(Float, configurable=False,
                                label='Actual duration', unit='sec',
                                depends_on='duration', store='attribute')
    coerced_samples = Property(Int, depends_on='coerced_duration')
    amplitude = Range(0.0, 10.0, value=1, unit='volt', store='attribute')

    duration = CFloat(1.0, configurable=True, label='Requested duration',
                      unit='sec', store='attribute')
    t = Property(Array(dtype='f'), depends_on='coerced_duration, fs')
    period = Property(Float)
    attenuation = Range(0.0, 120.0, value=60, configurable=True,
                        label='Attenuation', unit='dB ATT', store='attribute')
    variable = Str(editor=EnumEditor(name='parameters'), store='attribute')

    #variables_store = Property(Str, depends_on='variables', store='attribute')
    #variables = List(Str, [])
    #static = Bool(False)

    #average_power = Property(Float)
    #rms_power = Property(Float)
    parameters = Property

    def amplitude_sf(self, dB):
        '''Compute the scaling factor required to achieve the desired attenuation.
        '''
        if dB < 0:
            raise ValueError, 'dB < 0'
        sf = 10 ** (dB / 20.0)
        return 10.0 / sf

    def set_variable(self, par):
        if self.variable is not None:
            log.debug('Setting %r %s to %r', self, self.variable, par)
            setattr(self, self.variable, par)
        else:
            raise ValueError, 'No variable configured for this signal'

    def _get_average_power(self):
        return (self.signal ** 2).mean()

    def _get_rms_power(self):
        return self.average_power ** 0.5

    def _get_variables_store(self):
        return ', '.join(self.variables)

    def __len__(self):
        return len(self.t)

    def _get_t(self):
        return np.arange(0, self.coerced_duration, self.fs ** -1)

    def _get_coerced_samples(self):
        return self.coerced_duration * self.fs

    def _get_coerced_duration(self):
        cycles = int(self.duration / self.period)
        return cycles * self.period

    def _read(self, o, l):
        return self.signal[o:o + l]

    def __str__(self):
        configurable = self.class_trait_names(configurable=True)
        name = self.__class__.__name__

        # Unicode characters are not handled well by the console
        #base = u' \n\u00B7 %s: '
        base = '\n - %s: '
        for c in configurable:
            trait = self.trait(c)
            if c == self.variable:
                name += (base + ' variable (%s)') % (trait.label, trait.unit)
            else:
                value = getattr(self, c)
                try:
                    name += (base + ' %g %s') % (trait.label, value, trait.unit)
                except:
                    name += (base + ' %r %s') % (trait.label, value, trait.unit)
        return name

    def class_parameters(self, allow_none=False):
        traits = self.class_traits(configurable=True)
        display = [(name, trait.label) for name, trait in traits.items()]
        display = dict(display)
        if allow_none:
            display['none'] = None
        return display

    def _get_parameters(self):
        return self.class_parameters(allow_none=True)

    def parameter_view(self, parent=None):
        return signal_view_factory(self)

    def parameter_popup_view(self, parent=None):
        return View('handler.edit_signal{}', handler=SignalEditHandler)

    def preferred_attenuation(self, calibration):
        raise NotImplementedError, 'Use a subclass of signal'

if __name__ == '__main__':
    from cns.signal import type
    #t = type.Tone(calibration=DummyCalibration())
    #t.level = 90
    #Signal().configure_traits(view='parameter_popup')

    #type.Tone().configure_traits(view='parameter_popup_view')
