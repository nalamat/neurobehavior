import re
import time
import os

from enthought.etsconfig.etsconfig import ETSConfig
from enthought.savage.traits.ui.svg_button import SVGButton
from enthought.traits.api import CFloat, Constant, Instance, Bool, HasTraits, \
        Any, Button
from enthought.traits.ui.api import Controller, Item, HGroup, View
from cns.widgets import icons
from enthought.pyface.timer.api import Timer
from cns.equipment import EquipmentError

import logging
log = logging.getLogger(__name__)

'''This file contains four key classes.  These four classes work together to
separate out functionality into specific modules:

    PumpInterface - Handles communication with the pump hardware (e.g. changing
    rate, querying volume dispensed, determining whether there's an error)
    PumpController - Contains logic for responding to user interaction (e.g.
    what should happen when the "override" button is pressed?).
    pump_view - What information should the GUI have?
    Pump - The settings for the pump.

By splitting out functionality like this, we can swap in a different class if we
want the behavior to be different.  For example, we can use a different "view"
class to change how the GUI looks.  If we don't like how the current
"handler/controller" (which determines what commands to send to the pump based
on user input), we can write a different handler.  Finally, a new PumpInterface
can be written if we ever use a pump from a different manufacturer.  As long as
it knows how to transmit commands to the pump (as determined by the
PumpController).

pump_view <-> PumpController <-> Pump
                                 PumpInterface
'''

#####################################################################
# Custom-defined pump error messages
#####################################################################
# We could use the built-in error and exception classes, but I subclass these
# exceptions so that we can provide messages and information specific to
# problems with the pump hardware.

import serial
connection_settings = dict(port=0, baudrate=19200, bytesize=8, parity='N',
        stopbits=1, timeout=1, xonxoff=0, rtscts=0, writeTimeout=1,
        dsrdtr=None, interCharTimeout=None)
SERIAL = serial.Serial(**connection_settings)

class PumpError(EquipmentError):

    def __init__(self, code, cmd):
        self.code = code
        self.cmd = cmd

    def __str__(self):
        return '%s\n\n%s: %s' % (self._todo, self.cmd, self._mesg[self.code])

class PumpCommError(PumpError):
    '''Handles error messages carried by the RS232 response packets from the
    pump.'''

    _mesg = {
            # Actual codes returned by the pump
            ''      : 'Command is not recognized',
            'NA'    : 'Command is not currently applicable',
            'OOR'   : 'Command data is out of range',
            'COM'   : 'Invalid communications packet recieved',
            'IGN'   : 'Command ignored due to new phase start',
            # Custom codes
            'NR'    : 'No response from pump'
            }

    _todo = 'Unable to connect to pump.  Please ensure that no other ' + \
            'programs that utilize the pump are running and try ' + \
            'try power-cycling the entire system (rack and computer).'

class PumpHardwareError(PumpError):
    '''Handles errors specific to the pump hardware itself.'''

    _mesg = {
            'R'     : 'Pump was reset due to power interrupt',
            'S'     : 'Pump motor is stalled',
            'T'     : 'Safe mode communication time out',
            'E'     : 'Pumping program error',
            'O'     : 'Pumping program phase out of range',
            }

    _todo = 'Pump has reported an error.  Please check to ensure pump motor ' + \
            'is not over-extended and power-cycle the pump.'

class PumpUnitError(Exception):
    # This is a custom error I added that is not part of the pump interface
    # description.

    def __init__(self, expected, actual, cmd):
        self.expected = expected
        self.actual = actual
        self.cmd = cmd

    def __str__(self):
        mesg = '%s: Expected units in %s, receved %s'
        return mesg % (self.cmd, self.expected, self.actual)

class PumpInterface(object):
    # The Syringe Pump uses a standard 8N1 frame with a default baud rate of
    # 19200.  These are actually the default parameters when calling the command
    # to init the serial port, but I define them here for clarity.
    connection_settings = dict(port=0, baudrate=19200, bytesize=8, parity='N',
            stopbits=1, timeout=1, xonxoff=0, rtscts=0, writeTimeout=1,
            dsrdtr=None, interCharTimeout=None)

    #####################################################################
    # Basic information required for creating and parsing RS-232 commands
    #####################################################################

    # Hex command characters used to indicate state of data
    # transmission between pump and computer.
    ETX = '\x03'    # End of packet transmission
    STX = '\x02'    # Start of packet transmission
    CR = '\x0D'    # Carriage return

    _status = dict(I='infusing', W='withdrawing', S='halted', P='paused',
                   T='in timed pause', U='waiting for trigger', X='purging')

    # The response from the pump always includes a status flag which indicates
    # the pump state (or error).  We'll store the "latest" response from the
    # pump in _cur_status to get an idea of what the state is if we ever need
    # it.  Use with caution though, as the state of the pump is also controlled
    # by external factors (e.g. the spout contact circuit) so it could have
    # changed since the last time the pump was polled.
    _cur_status = None

    # Response is in the format <STX><address><status>[<data>]<ETX>
    _basic_response = re.compile(STX + '(?P<address>\d+)' + \
                                     '(?P<status>[IWSPTUX]|A\?)' + \
                                     '(?P<data>.*)' + ETX)

    # Response for queries about volume dispensed.  Returns separate numbers for
    # infuse and withdraw.  Format is I<float>W<float><units>
    _dispensed = re.compile('I(?P<infuse>[\.0-9]+)' + \
                            'W(?P<withdraw>[\.0-9]+)' + \
                            '(?P<units>[MLU]{2})')

    class Map(object):
        '''Helper class that allows us to do specify human-readable names and
        the corresponding machine code.  When __getitem__ is called, it will
        inspect both the human-readable name and machine code name until it
        finds a match.  It returns the "partner" of that match (e.g. if it
        matches the human-readable name, it will return the machine code that
        corresponds to the human-readable name.

        Note that __init__ and __getitem__ are special classmethods.  See Python
        documentation for more information about these.
        '''

        def __init__(self, **kw):
            self.map = kw

        def __getitem__(self, item):
            for a, b in self.map.items():
                if a.upper() == item.upper(): return b
                elif b.upper() == item.upper(): return a
            raise KeyError, item

    # These are unique one-way maps between the RS-232 command codes and a more
    # human-readable code that we can use in our programs.
    _direction = Map(infuse='INF', withdraw='WDR', reverse='REV')
    _trg = Map(start='St', run_high='LE')

    # Startup sequence that ensures pump is always in an expected state.
    _connect_seq = [
            # Pump baudrate must match connection baudrate otherwise we won't be
            # able to communicate
            'ADR 0 B %d' % connection_settings['baudrate'],
            # Set trigger to start pumping on rising TTL and stop on falling
            # TTL.  This should already be programmed in, but we confirm it to
            # be sure.
            'TRG LE',
            # Set volume units to mL
            'VOL ML',
            # Turn audible alarm off.  We will transmit error messages via the
            # the computer GUI.
            'AL 0',
            # Lockout keypad so user can only change settings via the computer!
            'LOC 0',
            'STP',
            ]

    # Disconnect sequence ensuring that pump is set to a state where it can be
    # used manually or with one of the older behavior programs.
    _disconnect_seq = [
            # Change keypad lockout so that user can change rate and direction,
            # but not the program settings.  There is no need for anyone to be
            # messing with the other settings.
            #'LOC P 1',
            #'LOC 0',
            # Turn the alarm back on for manual use (alarm will go off when the
            # pump stalls, for instance).
            'AL 1',
            ]

    #####################################################################
    # Special functions for controlling pump
    #####################################################################

    def __init__(self):
        self.connect()

    def connect(self):
        try: self.ser.close()
        except: pass
        try:
            self.ser = SERIAL
            for cmd in self._connect_seq:
                try:
                    self.xmit(cmd)
                except PumpCommError, e:
                    if e.code != 'NA':
                        raise

            # Ensure that pump is restored to initial state on system exit
            import atexit
            atexit.register(self.disconnect)

        except PumpHardwareError, e:
            # We want to trap and dispose of one very specific exception code,
            # 'R', which corresponds to a power interrupt.  This is almost
            # always returned when the pump is first powered on and initialized
            # so it really is not a concern to us.  The other error messages are
            # of concern so we reraise them.
            if e.code != 'R':
                raise

    def disconnect(self):
        for cmd in self._disconnect_seq:
            self.xmit(cmd)
        #self.ser.close()

    def run(self, **kw):
        '''Sets the appropriate properties of the pump and starts running.  This
        command ignores the state of the TTL, however future changes to the TTL
        can change the state of the pump (depending on what the trigger mode is
        set to).  To allow pump to run continuously without being affected by
        changes to the TTL level, pass trigger='start' as one of the
        arguments.

        e.g. pump.run(trigger='start', volume=10, rate=1.0) will cause the pump
        to continuously dispense 10 mL at a rate of 1 mL/min.
        '''
        for k, v in kw.items():
            setattr(self, k, v)
        if self.cur_status not in 'IW':
            self.start()
            #self.xmit('RUN')

    def run_if_TTL(self, **kw):
        '''In contrast to run, the state of the TTL is inspected.  If the TTL is
        high, and the pump is stopped, a RUN command will be sent.  If the TTL
        state is low and the pump is running, a STOP command will be sent.

        The goal of this function is to allow an easy way to smoothly switch
        from an override mode where the TTL logic is ignored to a mode in which
        the TTL logic controls the pump (also change rate while an animal is
        drinking).

        TODO: This handling does not factor in TTL modes where a low or falling
        edge is meant to START the pump (not stop it).  Right now we do not have
        a need for this, so I will not worry about it.
        '''
        # Some changes to properties are stored in volatile memory if the pump
        # is currently executing a program.  Once the pump stops (e.g. if the
        # gerbil comes off the spout), then the changes are lost.  By stopping
        # the pump, we can ensure these changes are stored in non-volatile
        # memory.
        self.stop()
        for k, v in kw.items():
            setattr(self, k, v)
        # Store value in a local variable so we don't have to send a new RS232
        # command the next time we need the value
        TTL = self.TTL
        if TTL and self.cur_status not in 'IW':
            #self.xmit('RUN')
            self.run()
        elif not TTL and self.cur_status in 'IW':
            self.stop()
            #self.xmit('STP')

    def reset_volume(self):
        self.xmit('CLD INF')
        self.xmit('CLD WDR')

    def stop(self):
        self.xmit('STP')

    def start(self):
        self.xmit('RUN')

    #####################################################################
    # Property get/set for controlling pump parameters
    #####################################################################
    # Note these are not meant to be called directly.  They are "special"
    # methods.  When you call pump.trigger, it is translated to
    # pump._get_trigger().  When you call pump.trigger='start', it is translated
    # to pump._set_trigger('start').

    def _set_trigger(self, trg):
        self.xmit('TRG %s' % self._trg[trg])

    def _get_trigger(self):
        return self._trg[self.xmit('TRG')]

    def _set_volume(self, volume):
        self.xmit('VOL %0.2f' % volume)

    def _get_volume(self):
        data = self.xmit('VOL')
        if data[-2:] != 'ML':
            raise PumpUnitError('ML', data[-2:], 'VOL')
        return float(data[:-2])

    def _get_direction(self):
        dir = self.xmit('DIR')
        if dir == 'INF': return 'infuse'
        elif dir == 'WDR': return 'withdraw'
        else: raise PumpCommError('', 'DIR')

    def _set_direction(self, direction):
        return self.xmit('DIR %s' % self._direction[direction])

    def _set_rate(self, rate):
        # Units are UM MM UH MH.  First character indicates ul or ml, second
        # character indicates min or hour.  RAT C tells the pump to change the
        # rate and continue running.  If the pump is running when the rate is
        # changed, then it is stored in volatile memory.  Thus, the pump will
        # revert to the old rate when the program resets (note that when the
        # animal comes off the spout, the program is paused so the rate stored
        # in volatile memory remains in effect.  It isn't until you hit a button
        # on the keypad or power-cycle the pump that the pump reverts to the old
        # rate.

        # NOTE: RAT C does not work with the older pump.
        if rate < 0: self.direction = 'withdraw'
        else: self.direction = 'infuse'
        #self.stop()
        self.xmit('RAT C %.3f' % abs(rate))
        #self.start()

    def _get_rate(self):
        rate = self.xmit('RAT')
        if rate[-2:] != 'MM':
            raise PumpUnitError('MM', rate[-2:], 'RAT')
        return float(rate[:-2])

    def _get_dispensed(self, direction):
        # Helper method for _get_infused and _get_withdrawn
        result = self.xmit('DIS')
        match = self._dispensed.match(result)
        if match.group('units') != 'ML':
            raise PumpUnitError('ML', match.group('units'), 'DIS')
        else:
            return float(match.group(direction))

    def _get_infused(self):
        return self._get_dispensed('infuse')

    def _get_withdrawn(self):
        return self._get_dispensed('withdraw')

    def _set_diameter(self, diameter):
        self.xmit('DIA %.2f' % diameter)

    def _get_diameter(self):
        self.xmit('DIA')

    def _get_ttl(self):
        data = self.xmit('IN 2')
        if data == '1': return True
        elif data == '0': return False
        else: raise PumpCommError('', 'IN 2')

    # The actual property definitions
    infused = property(_get_infused)
    withdrawn = property(_get_withdrawn)
    volume = property(_get_volume, _set_volume)
    direction = property(_get_direction, _set_direction)
    rate = property(_get_rate, _set_rate)
    diameter = property(_get_diameter, _set_diameter)
    trigger = property(_get_trigger, _set_trigger)
    TTL = property(_get_ttl)

    #####################################################################
    # RS232 functions
    #####################################################################

    def _basic_xmit(self, cmd):
        '''Takes command and formats it for transmission to the pump.  Inspects
        resulting response packet to see if the pump is operating within
        expected parameters.  If not, an error is raised, otherwise the data is
        extracted from the pump and returned.

        All commands are logged for debugging.
        '''
        self.ser.write(cmd + self.CR)
        #log.debug('Sent %s to pump', cmd)
        result = self.ser.readline(eol=self.ETX)
        if not result:
            raise PumpCommError('NR', cmd)
        #log.debug('Pump returned raw response: %s' % result)
        match = self._basic_response.match(result)

        if match.group('status') == 'A?':
            raise PumpHardwareError(match.group('data'), cmd)
        elif match.group('data').startswith('?'):
            raise PumpCommError(match.group('data')[1:], cmd)

        self.cur_status = match.group('status')
        return match.group('data')

    # At one point we were considering adding a _safe_xmit mode, however I got
    # tired of trying to get it to work so I gave up.  I'm leaving this as-is in
    # case we ever decide to revisit the issue.  The safe mode code is below but
    # commented out.
    xmit = _basic_xmit

    # TODO: safe mode code is not working.  This is just a placeholder if we
    # ever decide to revisit this issue.  I'm not interested in debugging the
    # issues pertaning to this right now.
    #mode = Enum('basic', 'safe')
    #safe_timeout = Int(150)

    # If pump starts up in safe mode, we can disable it
    #exit_safe = STX+'\x08SAF0\x55\x43'+ETX

    # Response is in the format <STX><address><status>[<data>]<ETX>
    #_safe_response = re.compile(STX+'(\d+)([IWSPTUX])(.*)'+ETX)

    #def _xmit_safe(self, cmd):
    #    # Format is <STX><length><command data><CRC 16><ETX>
    #    # Length is remaining bytes in packet, including length byte
    #    # CRC 16 is high byte, low byte of 16 bit CCITT CRC

    #    # 4 includes two byte CRC, length byte, and ETX byte
    #    length = len(cmd)+4
    #    crc = util.crc_compute(cmd)
    #    hi, lo = util.hi8(crc), util.lo8(crc)

    #    self.ser.write(length)
    #    self.ser.write(cmd)
    #    self.ser.write(hi)
    #    self.ser.write(lo)
    #    self.ser.write(self.ETX)
    #    log.debug('Sent %s %s %s %s to pump' % \
    #            (hex(length), cmd, hex(hi), hex(lo)))

    #    result = self.ser.readline(eol=self.ETX)
    #    addr, status, resp = self._basic_response.match(result).groups()

class PumpToolBar(HasTraits):
    '''Toolbar containing command buttons that allow us to control the pump via
    a GUI.  Three basic commands are provided: increase rate, decrease rate, and
    override the TTL input (so pump continuously infuses).  There are two
    additional commands, intialize and shutdown, which essentially infuse or
    withdraw, respectively, a fixed volume.  This would be used at the start or
    end of an experiment to fill the tube or drain it.  However, we do not
    include buttons for these on the toolbar to prevent the user from
    accidentally clicking on them during an experiment!
    '''

    handler = Any

    # There are two primary backends for the GUI system we are using: QT4 and
    # WxWidgets.  WxWidgets has an ugly SVG button renderer, so we use
    # text-based buttons when  using WxWidgets.  When QT4 is the active backend,
    # we can use some pretty-looking SVG buttons (that show the toggle state).
    if ETSConfig.toolkit == 'qt4':
        kw = dict(height=18, width=18)
        increase = SVGButton(filename=icons.up, **kw)
        decrease = SVGButton(filename=icons.down, **kw)
        override = SVGButton(filename=icons.right2, tooltip='override', toggle=True, **kw)
        #initialize  = SVGButton(filename=icons.first, **kw)
        #shutdown    = SVGButton(filename=icons.last, **kw)
        item_kw = dict(show_label=False)
    else:
        increase = Button('+')
        decrease = Button('-')
        override = Button('O')
        initialize = Button('I')
        shutdown = Button('W')
        item_kw = dict(width= -24, height= -24, show_label=False)

    group = HGroup(Item('increase', **item_kw),
                   Item('decrease', **item_kw),
                   Item('override', **item_kw),
                   '_',
                   )

    traits_view = View(group)

    def _increase_fired(self, event):
        self.handler.do_increase(self.handler.info)

    def _decrease_fired(self, event):
        self.handler.do_decrease(self.handler.info)

    def _override_fired(self, event):
        # TODO: we should probably consider adding some code to update the look
        # of the override button when it's in text mode so the user has some
        # visual feedback that the pump is in 'override' mode.
        self.handler.do_toggle_override(self.handler.info)

    def _initialize_fired(self, event):
        self.handler.do_initialize(self.handler.info)

    def _shutdown_fired(self, event):
        self.handler.do_shutdown(self.handler.info)

class PumpController(Controller):

    toolbar = Instance(PumpToolBar, args=())
    iface = Instance(PumpInterface, args=())
    override = Bool(False)
    monitor = Bool(True)
    model = Any

    timer = Instance(Timer)

    def init(self, info):
        #self.iface.connect()
        # This is what we call "installing the handler".  Essentially we are
        # giving the GUI toolbar a reference to the handler so it can
        # communicate user actions to the handler as needed.
        self.toolbar.handler = self
        self.model = info.object
        self.iface = PumpInterface()
            
        if self.monitor:
            self.timer = Timer(250, self.tick)

    def tick(self):
        self.model.infused = self.iface.infused
        self.model.withdrawn = self.iface.withdrawn

    #####################################################################
    # Logic for processing of user actions
    #####################################################################
    def do_fill_tube(self, info):
        self.iface.reset_volume()
        self.iface.run(rate=info.object.fill_rate,
                       volume=info.object.tube_volume,
                       trigger='start')

        while self.iface.infused < info.object.tube_volume:
            time.sleep(0.25)

        self.iface.reset_volume()
        self.iface.volume = 0

    def do_empty_tube(self, info):
        self.iface.reset_volume()
        self.iface.run(rate= -info.object.fill_rate,
                       volume=info.object.tube_volume,
                       trigger='start')

        while self.iface.withdrawn < info.object.tube_volume:
            time.sleep(0.25)

        self.iface.reset_volume()
        self.iface.volume = 0
        self.trigger = 'run_high'

    def do_toggle_override(self, info):
        if self.iface.trigger == 'run_high':
            self.iface.run(trigger='start')
            self.override = True
        else:
            self.iface.run_if_TTL(trigger='run_high')
            self.override = False

    def do_increase(self, info):
        info.object.rate += info.object.rate_incr

    def do_decrease(self, info):
        info.object.rate -= info.object.rate_incr

    #####################################################################
    # How changes to the model are handled
    #####################################################################
    # If there are any changes to the model, either via the program or via user
    # interaction, we need to ensure that the pump settings are updated
    # properly.  These commands listen for changes and apply the necessary
    # changes to the pump.  For example, calling pump.do_increase() causes the
    # rate property of the model to change.  This change results in
    # object_rate_changed being called.  object_rate_change then tells
    # PumpInterface to update the rate.

    def object_rate_changed(self, info):
        self.iface.rate = info.object.rate
        info.object.rate = self.iface.rate

    def object_diameter_changed(self, info):
        self.iface.diameter = info.object.diameter

    def object_trigger_changed(self, info):
        self.iface.trigger = info.object.trigger

class Pump(HasTraits):
    '''Contains the pump settings.
    '''
    rate = CFloat(0.3, label='Rate (mL/min)', store='attribute')
    diameter = Constant(19.05, label='Syringe ID (mm)', store='attribute')
    trigger = Constant('run_high', store='atribute')

    #infused = CFloat(0)
    #withdrawn = CFloat(0)

    # \u0394 is the unicode character code for the Greek uppercase delta.
    rate_incr = CFloat(0.025, label=u'\u0394 Rate (mL/min)', store='attribute')

    # Approximate volume of the tube connecting the pump to the lick spout
    tube_volume = CFloat(4.0, label='Tube volume (mL)', store='attribute')
    # Fastest (safe) rate at which we can fill the tube
    fill_rate = CFloat(10.0, label='Tube fill rate (mL/min)', store='attribute')

    traits_view = View(['handler.toolbar{}@', 'rate_incr', 'rate', '-'],
                        handler=PumpController)

if __name__ == '__main__':
    try:
        pump = Pump()
        pump.configure_traits()
    except EquipmentError:
        print 'error'
