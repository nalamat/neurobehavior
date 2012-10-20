'''
Created on Jul 12, 2010

@author: Brad
'''

from cns.equipment.calibration import MicrophoneCalibration, SpeakerCalibration
from pyface.api import GUI, OK
from pyface.wizard.api import SimpleWizard, WizardPage, WizardController
from traitsui.api import View
from traits.api import Instance, Str, HasTraits, on_trait_change

miccalsetup_mesg = \
'''The first step is to determine the actual sensitivity of the microphone using
a pistonphone.  Please indicate which pistonphone and microphone you are using.
If you wish to skip this step and use the nominal sensitivity of the microphone,
you can specify a value of none.'''

miccalready_mesg = \
'''Please turn on the pistonphone.'''

miccalskipped_mesg = \
'''You did not select a pistonphone so you need to specify the microphone's
actual sensitivity.  Its nominal sensitivity (as reported by the manufacturer)
is already entered below.  If you wish to specify a different value (e.g., if
you've used this microphone before and know it's been damaged), please do so
now.'''

class WizCalController(WizardController):

    def _current_page_changed(self, new):
        new.start()

class MicCal(WizardPage):

    cal = Instance(MicrophoneCalibration, ())

    def start(self):
        pass

class MicCalSetup(MicCal):

    id = 'MicCalSetup'
    heading = 'Select microphone and pistonphone'
    subheading = miccalsetup_mesg

    def _create_page_content(self, parent):
        self.cal.on_trait_change(self._on_change, '+')
        view = View('standard{Pistonphone}', 'microphone')
        self._on_change()
        return self.cal.edit_traits(view=view).control

    def _on_change(self):
        if self.cal.microphone is not None and self.cal.standard is None:
            self.complete = True
            self.next_id = 'MicCalSkipped'
        elif self.cal.microphone is not None or self.cal.standard is not None:
            self.complete = True
            self.next_id = 'MicCalReady'
        else:
            self.complete = False

class MicCalReady(MicCal):

    id = 'MicCalReady'
    heading = 'Calibrating microphone'
    subheading = 'Please turn on the pistonphone.'
    complete = True
    next_id = 'MicCalDo'

    def _create_page_content(self, parent):
        view = View('duration{Duration to monitor (s)}',
                    'averages{Number of averages}')
        return self.cal.edit_traits(view=view).control

class MicCalDo(MicCal):

    id = 'MicCalDo'
    heading = 'Microphone sensitivity'

    def _create_page_content(self, parent):
        view = View(Item('object.microphone.actual_sens',
                         label='Measured Sensitivity (Vrms/Pa)'))
        return self.cal.edit_traits(view=view).control

    def start(self):
        self.cal.microphone.actual_sens = 43
        #sens = calibration.ref_cal(self.cal.ref_duration, self.cal.ref_averages,
        #        fft=true)
        #calibration.ref_cal(

class RefCalSkipped(RefCal):

    id = 'RefCalSkipped'
    heading = 'Skipping microphone calibration'
    subheading = refcalskipped_mesg
    complete = True

    @on_trait_change('cal.microphone, cal.standard')
    def _cal_changed(self):
        self.cal.microphone.actual_sens = self.cal.microphone.nominal_sens

    def _create_page_content(self, parent):
        view = View('object.microphone.actual_sens{Actual sensitivity (Vrms/Pa)}')
        return self.cal.edit_traits(view=view).control

class RefCal(WizardPage):

    def _create_page_content(self, parent):
        pass


if __name__ == '__main__':
    gui = GUI()
    cal = Calibration()
    pages = [RefCalSetup, RefCalReady, RefCalSkipped, RefCalDo]
    pages = [page(cal=cal) for page in pages]
    #pages = [RefCalSetup(), RefCalReady(), RefCalSkipped()]
    #pages = [RefCalSetup(), RefCalReady()]

    wizard = SimpleWizard(parent=None, pages=pages,
            controller=WizCalController())
    if wizard.open() == OK:
        print 'success'
