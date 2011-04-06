# -*- coding: utf-8 -*-

import re
import logging
import serial

log = logging.getLogger(__name__)

def convert(value, src_unit, dest_unit):
    MAP = {
            ('ul',     'ml'):     lambda x: x*1e-3,
            ('ml',     'ul'):     lambda x: x*1e3,
            ('ul/min', 'ml/min'): lambda x: x*1e-3,
            ('ul/min', 'ul/h'):   lambda x: x*60.0,
            ('ul/min', 'ml/h'):   lambda x: x*60e-3,
            ('ml/min', 'ul/min'): lambda x: x*1e3,
            ('ml/min', 'ul/h'):   lambda x: x*60e3,
            ('ml/min', 'ml/h'):   lambda x: x*60,
            ('ul/h',   'ml/h'):   lambda x: x*1e-3,
            }
    if src_unit == dest_unit:
        return value
    return MAP[src_unit, dest_unit](value)

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

    STATUS = dict(I='infusing', W='withdrawing', S='halted', P='paused',
                   T='in timed pause', U='waiting for trigger', X='purging')

    '''
    Map of trigger modes.  Dictionary key is the value that must be provided
    with the TRG command sent to the pump.  Value is a two-tuple indicating the
    start and stop trigger for the pump (based on the TTL input).  The trigger
    may be a rising/falling edge, a low/high value or None.  If you set the
    trigger to 'falling', None', then a falling TTL will start the pump's
    program with no stop condition.  A value of 'rising', 'falling' will start
    the pump when the input goes high and stop it when the input goes low.
    '''
    TRIG_MODE = {
            'FT':   ('falling', 'falling'),
            'FH':   ('falling', 'rising'),
            'F2':   ('rising',  'rising'),
            'LE':   ('rising',  'falling'),
            'ST':   ('falling', None),
            'T2':   ('rising',  None),
            'SP':   (None,      'falling'),
            'P2':   (None,      'falling'),
            'RL':   ('low',     None),
            'RH':   ('high',    None),
            'SL':   (None,      'low'),
            'SH':   (None,      'high'),
            }

    REV_TRIG_MODE = dict((v, k) for k, v in TRIG_MODE.items())

    DIR_MODE = {
            'INF':  'infuse',
            'WDR':  'withdraw',
            'REV':  'reverse',
            }

    REV_DIR_MODE = dict((v, k) for k, v in DIR_MODE.items())

    RATE_UNIT = {
            'UM':   'ul/min',
            'MM':   'ml/min',
            'UH':   'ul/h',
            'MH':   'ml/h',
            }

    REV_RATE_UNIT = dict((v, k) for k, v in RATE_UNIT.items())

    VOL_UNIT = {
            'UL':   'ul',
            'ML':   'ml',
            }

    REV_VOL_UNIT = dict((v, k) for k, v in VOL_UNIT.items())

    # The response from the pump always includes a status flag which indicates
    # the pump state (or error).  Response is in the format
    # <STX><address><status>[<data>]<ETX>
    _basic_response = re.compile(STX + '(?P<address>\d+)' + \
                                       '(?P<status>[IWSPTUX]|A\?)' + \
                                       '(?P<data>.*)' + ETX)

    # Response for queries about volume dispensed.  Returns separate numbers for
    # infuse and withdraw.  Format is I<float>W<float><units>
    _dispensed = re.compile('I(?P<infuse>[\.0-9]+)' + \
                            'W(?P<withdraw>[\.0-9]+)' + \
                            '(?P<units>[MLU]{2})')

    ser = serial.Serial(**connection_settings)

    #####################################################################
    # Special functions for controlling pump
    #####################################################################

    def __init__(self, start_trigger='rising', stop_trigger='falling',
            volume_unit='ml', rate_unit='ml/min'):
        self.connect()

        # We do not currently support changing the units of the pump on-the-fly.
        # They must be initialized here.
        self.rate_unit = rate_unit
        self.volume_unit = volume_unit
        self.rate_unit_cmd = self.REV_RATE_UNIT[rate_unit]
        self.volume_unit_cmd = self.REV_VOL_UNIT[volume_unit]
        self.xmit('VOL %s' % self.volume_unit_cmd)
        self.set_trigger(start=start_trigger, stop=stop_trigger)

    def connect(self):
        try:
            if not self.ser.isOpen():
                self.ser.open()

            # Pump baudrate must match connection baudrate otherwise we won't be
            # able to communicate
            self.xmit('ADR 0 B %d' % self.connection_settings['baudrate'])
            # Turn audible alarm on.  This will notify the user of any problems
            # with the pump.
            self.xmit('AL 1')
            # Ensure that serial port is closed on system exit
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
            log.exception(e)
            raise PumpCommError('SER')

    def disconnect(self):
        self.ser.close()

    def run(self):
        self.start()

    def run_if_TTL(self):
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
        if self.get_TTL():
            self.run()
        else:
            self.stop()

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
    def set_trigger(self, start, stop):
        cmd = self.REV_TRIG_MODE[start, stop]
        self.xmit('TRG %s' % cmd)

    def get_direction(self):
        value = self.xmit('DIR')
        return self.REV_DIR_MODE[value]

    def set_direction(self):
        arg = self.REV_DIR_MODE[direction]
        self.xmit('DIR %s' % arg)

    def get_rate(self, unit=None):
        value = self.xmit('RAT')
        if value[-2:] != self.rate_unit_cmd:
            raise PumpUnitError(self.volume_unit_cmd, value[-2:])
        value = float(value[:-2])
        if unit is not None:
            value = convert(value, self.rate_unit, unit)
        return value

    def set_rate(self, rate, unit=None):
        if unit is not None:
            rate = convert(rate, unit, self.rate_unit)
        self.xmit('RAT %0.3f %s' % (rate, self.rate_unit_cmd))

    def set_volume(self, volume, unit=None):
        if unit is not None:
            volume = convert(volume, unit, self.volume_unit)
        self.xmit('VOL %0.3f' % volume)

    def get_volume(self, unit=None):
        value = self.xmit('VOL')
        if value[-2:] != self.volume_unit_cmd:
            raise PumpUnitError(self.volume_unit_cmd, value[-2:])
        value = float(value[:-2])
        if unit is not None:
            value = convert(value, unit, self.volume_unit)
        return value

    def _get_dispensed(self, direction, unit=None):
        # Helper method for _get_infused and _get_withdrawn
        result = self.xmit('DIS')
        match = self._dispensed.match(result)
        if match.group('units') != self.volume_unit_cmd:
            raise PumpUnitError('ML', match.group('units'), 'DIS')
        else:
            value = float(match.group(direction)) 
            if unit is not None:
                value = convert(value, self.volume_unit, unit)
            return value

    def get_infused(self, unit=None):
        return self._get_dispensed('infuse', unit)

    def get_withdrawn(self, unit=None):
        return self._get_dispensed('withdraw', unit)

    def set_diameter(self, diameter, unit=None):
        if unit is not None and unit != 'mm':
            raise PumpUnitError('mm', unit, 'DIA')
        self.xmit('DIA %.2f' % diameter)

    def get_diameter(self):
        self.xmit('DIA')

    def get_TTL(self):
        data = self.xmit('IN 2')
        if data == '1': 
            return True
        elif data == '0': 
            return False
        else: 
            raise PumpCommError('', 'IN 2')

    #####################################################################
    # RS232 functions
    #####################################################################

    def readline(self):
        # PySerial v2.5 no longer supports the eol parameter, so we manually
        # read byte by byte until we reach the line-end character.  Timeout
        # should be set to a very low value as well.  A support ticket has been
        # filed (and labelled WONTFIX).
        # https://sourceforge.net/tracker/?func=detail&atid=446302&aid=3101783&group_id=46487 
        result = []
        while 1:
            last = self.ser.read(1)
            result.append(last)
            if last == self.ETX or last == '':
                break
        return ''.join(result)

    def xmit_sequence(self, commands):
        return [self.xmit(cmd) for cmd in commands]
        for cmd in cmds:
            self.xmit(cmd)

    def xmit(self, cmd):
        '''
        Takes command and formats it for transmission to the pump.  Inspects
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

if __name__ == "__main__":
    import time
    pi = PumpInterface(volume_unit='ul', rate_unit='ml/min')
    print pi.set_volume(4)
    print pi.get_volume()
    print pi.set_rate(0.3)
    print pi.get_rate()
    print pi.get_rate(unit='ul/min')
    print pi.get_rate(unit='ul/h')
    pi.run()
    time.sleep(1)
    print pi.get_infused()
    print pi.get_infused(unit='ml')
    #pi.run()
    #time.sleep(1)
    #print pi.get_infused()
    #print pi.get_withdrawn()
