# -*- coding: utf-8 -*-

import re
import logging
import serial

log = logging.getLogger(__name__)

#####################################################################
# Custom-defined pump error messages
#####################################################################

class PumpError(BaseException):

    def __init__(self, code, mesg=None):
        self.code = code
        self.mesg = mesg

    def __str__(self):
        result = '%s\n\n%s' % (self._todo, self._mesg[self.code]) 
        if self.mesg is not None:
            result += ' ' + self.mesg
        return result

class PumpCommError(PumpError):
    '''Handles error messages resulting from problems with communication via the
    pump's serial port.'''

    _mesg = {
            # Actual codes returned by the pump
            ''      : 'Command is not recognized',
            'NA'    : 'Command is not currently applicable',
            'OOR'   : 'Command data is out of range',
            'COM'   : 'Invalid communications packet recieved',
            'IGN'   : 'Command ignored due to new phase start',
            # Custom codes
            'NR'    : 'No response from pump',
            'SER'   : 'Unable to open serial port',
            'UNK'   : 'Unknown error',
            }

    _todo = 'Unable to connect to pump.  Please ensure that no other ' + \
            'programs that utilize the pump are running and try ' + \
            'try power-cycling the entire system (rack and computer).'

class PumpHardwareError(PumpError):
    '''Handles errors specific to the pump hardware.'''

    _mesg = {
            'R'     : 'Pump was reset due to power interrupt',
            'S'     : 'Pump motor is stalled',
            'T'     : 'Safe mode communication time out',
            'E'     : 'Pumping program error',
            'O'     : 'Pumping program phase out of range',
            }

    _todo = 'Pump has reported an error.  Please check to ensure pump ' + \
            'motor is not over-extended and power-cycle the pump.'

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


print "\n\n\n\nLOADING MODULE\n\n\n"

class PumpInterface(object):

    #####################################################################
    # Basic information required for creating and parsing RS-232 commands
    #####################################################################

    # Hex command characters used to indicate state of data
    # transmission between pump and computer.
    ETX = '\x03'    # End of packet transmission
    STX = '\x02'    # Start of packet transmission
    CR  = '\x0D'    # Carriage return

    # The Syringe Pump uses a standard 8N1 frame with a default baud rate of
    # 19200.  These are actually the default parameters when calling the command
    # to init the serial port, but I define them here for clarity (especially if
    # they ever change in the future).
    connection_settings = dict(port=0, baudrate=19200, bytesize=8, parity='N',
            stopbits=1, timeout=.05, xonxoff=0, rtscts=0, writeTimeout=1,
            dsrdtr=None, interCharTimeout=None)

    _status = dict(I='infusing', W='withdrawing', S='halted', P='paused',
                   T='in timed pause', U='waiting for trigger', X='purging')

    # The response from the pump always includes a status flag which indicates
    # the pump state (or error).  We'll store the "latest" response from the
    # Response is in the format <STX><address><status>[<data>]<ETX>
    _basic_response = re.compile(STX + '(?P<address>\d+)' + \
                                       '(?P<status>[IWSPTUX]|A\?)' + \
                                       '(?P<data>.*)' + ETX)

    # Response for queries about volume dispensed.  Returns separate numbers for
    # infuse and withdraw.  Format is I<float>W<float><units>
    _dispensed = re.compile('I(?P<infuse>[\.0-9]+)' + \
                            'W(?P<withdraw>[\.0-9]+)' + \
                            '(?P<units>[MLU]{2})')

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

    ser = serial.Serial(**connection_settings)

    #####################################################################
    # Special functions for controlling pump
    #####################################################################

    def __init__(self):
        self.connect()

    def connect(self):
        #try: self.ser.close()
        #except: pass
        try:
            if not self.ser.isOpen():
                self.ser.open()
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
        except NameError, e:
            # Raised when it cannot find the global name 'SERIAL' (which
            # typically indicates a problem connecting to COM1).  Let's
            # translate this to a human-understandable error.
            print e
            raise PumpCommError('SER')

    def disconnect(self):
        for cmd in self._disconnect_seq:
            self.xmit(cmd)

    def run(self, **kw):
        '''Sets the appropriate properties of the pump and starts running.  This
        command ignores the state of the TTL, however future changes to the TTL
        can change the state of the pump (depending on what the trigger mode is
        set to).  To allow pump to run continuously without being affected by
        changes to the TTL level, pass trigger='start' as one of the
        arguments.

        To make the pump continuosly dispense 10 mL at a rate of 1 mL/min:

        >>>  pump.run(trigger='start', volume=10, rate=1.0) 
        '''
        for k, v in kw.items():
            setattr(self, k, v)
        if self.cur_status not in 'IW':
            self.start()

    def run_if_TTL(self, **kw):
        '''In contrast to `run`, the state of the TTL is inspected.  If the TTL is
        high, and the pump is stopped, a RUN command will be sent.  If the TTL
        state is low and the pump is running, a STOP command will be sent.

        The goal of this function is to allow an easy way to smoothly switch
        from an override mode where the TTL logic is ignored to a mode in which
        the TTL logic controls the pump (also change rate while an animal is
        drinking).

        This handling does not factor in TTL modes where a low or falling edge
        is meant to start the pump (not stop it).  Right now we do not have a
        need for this, so I will not worry about it.
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
        if trg == 'start':
            self.xmit('TRG St')
        elif trg == 'run_high':
            self.xmit('TRG LE')
        else:
            raise PumpCommError('', 'TRG')

    def _get_trigger(self):
        trig = self.xmit('TRG')
        if trig == 'ST':
            return 'start'
        elif trig == 'LE':
            return 'run_high'
        else:
            raise PumpCommError('', 'TRG ' + trig)

    def _set_volume(self, volume):
        self.xmit('VOL %0.2f' % volume)

    def _get_volume(self):
        data = self.xmit('VOL')
        if data[-2:] != 'ML':
            raise PumpUnitError('ML', data[-2:], 'VOL')
        return float(data[:-2])

    def _get_direction(self):
        dir = self.xmit('DIR')
        if dir == 'INF': 
            return 'infuse'
        elif dir == 'WDR': 
            return 'withdraw'
        else: 
            raise PumpCommError('', 'DIR')

    def _set_direction(self, direction):
        if direction == 'withdraw':
            return self.xmit('DIR WDR')
        elif direction == 'infuse':
            return self.xmit('DIR INF')
        elif direction == 'reverse':
            return self.xmit('DIR REV')
        else:
            raise PumpCommError('', 'DIR')

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
        if rate < 0: 
            self.direction = 'withdraw'
        else: 
            self.direction = 'infuse'

        try:
            self.xmit('RAT C %.3f' % abs(rate))
        except:
            # Our oldest pump does not support the RAT C command
            #self.stop()
            self.xmit('RAT %.3f' % abs(rate))
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
    infused     = property(_get_infused)
    withdrawn   = property(_get_withdrawn)
    volume      = property(_get_volume, _set_volume)
    direction   = property(_get_direction, _set_direction)
    rate        = property(_get_rate, _set_rate)
    diameter    = property(_get_diameter, _set_diameter)
    trigger     = property(_get_trigger, _set_trigger)
    TTL         = property(_get_ttl)

    #####################################################################
    # RS232 functions
    #####################################################################

    def readline(self):
        # PySerial v2.5 no longer supports the eol parameter, so we manually
        # read byte by byte until we reach the line-end character.  Timeout
        # should be set to a very low value as well.  A support ticket has been
        # filed.
        # https://sourceforge.net/tracker/?func=detail&atid=446302&aid=3101783&group_id=46487 
        result = []
        while 1:
            last = self.ser.read(1)
            result.append(last)
            if last == self.ETX or last == '':
                break
        return ''.join(result)

    def xmit(self, cmd):
        '''Takes command and formats it for transmission to the pump.  Inspects
        resulting response packet to see if the pump is operating within
        expected parameters.  If not, an error is raised, otherwise the data is
        extracted from the pump and returned.

        All commands are logged for debugging.
        '''
        self.ser.write(cmd + self.CR)
        result = self.readline()
        if result == '':
            raise PumpCommError('NR', cmd)
        match = self._basic_response.match(result)
        if match is None:
            raise PumpCommError('NR')
        if match.group('status') == 'A?':
            raise PumpHardwareError(match.group('data'), cmd)
        elif match.group('data').startswith('?'):
            raise PumpCommError(match.group('data')[1:], cmd)
        return match.group('data')
