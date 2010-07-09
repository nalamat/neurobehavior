import logging
log = logging.getLogger(__name__)

import rpcox
import actxobjects

'''The simplest way to connect to the TDT DSP devices is:

from cns import equipment
circuit = equipment.dsp().connect(circuit_name, device_name)

This returns an object that allows you to query and set variables in the DSP
code (i.e. "tags" as the TDT documentation refers to them) as well as read and
write access to the buffers.  See rpcox.py for more information.
'''

INTERFACE = 'GB'

drivers = {
        'RX6':  'RPcoX',
        'ZBUS': 'ZBUSx',
        'PA5':  'PA5x',
        'RZ5':  'RPcoX',
        }

RX6_OUT1    = 1
RX6_OUT2    = 2
RX6_IN1     = 128
RX6_IN2     = 129

def connect_zbus(interface='GB', ID=1):
    zbus = actxobjects.ZBUSx()
    if zbus.ConnectZBUS(interface):
        log.debug('Connected to zBUS via %s interface' % interface)
    else:
        mesg = 'Unable to connect to zBUS via %s interface'
        mesg = mesg % interface
        log.critical(mesg)

        # I've never seen GetError() actually return something other
        # than an empty string.  However, we'll log this string just in
        # case it does return useful information someday.
        error = zbus.GetError().strip()
        if len(error) == 0: log.debug('zBUS is not reporting any error')
        else: log.debug('zBUS returns an error: %s' % error)
        raise SystemError, mesg

    zbus.FlushIO(ID)
    # It seems like a good idea to make sure zBus triggers are configured to
    # low initially so there are no surprises.
    zbus.zBusTrigA(ID, 2, 2)
    zbus.zBusTrigB(ID, 2, 2)
    return zbus

def reset_zbus():
    try:
        zbus.HardwareReset()
        #zbus.Reset()
    except NameError:
        raise SystemError, 'Not connected to zBUS, cannot initiate reset.'

def connect(name, interface='GB', ID=1):
    debug_string = '%s %d via %s interface' % (name, ID, interface)
    driver = getattr(actxobjects, drivers[name])()

    if not getattr(driver, 'Connect%s' % name)(interface, ID):
        log.debug('Connect attempt for %s failed, resetting zBUS' % debug_string)
        reset_zbus()
        # Per conversation with TDT, a hardware reset often fixes issues with the
        # system.  Note that this function always returns False regardless of
        # whether it was successful or not.

        # Ok, now that we've reset the zBUS, let's give it another shot.  If it
        # fails again, we're going to have to give up as this cannot be fixed via
        # software.  Based on preliminary testing, it does not appear that a
        # HardwareReset affects the PA5 or RX6 connection; however, if we currently
        # have data "in the lines", this data may be lost.  At this point, we are
        # simply setting up the system, so this is not an issue.
        if not getattr(driver, 'Connect%s' % name)(interface, ID):
            log.debug('zBUS is reporting an error of: %s.' % ZBUS.GetError())
            raise SystemError, 'Unable to connect to %s.' % debug_string

    log.debug('Connected to %s' % debug_string)
    driver.ID = name
    return driver

try:
    # If you look at the code under the folder actxobjects, keep in mind that
    # this was auto-generated by Python the first time I connected to it with
    # the win32com library.  By caching this file, we save a lot of overhead by
    # referencing the cache directly so Python does not have to re-query the
    # RPcoX library each time (such querying allows Python to discover what
    # functions the library supports).
    import actxobjects
    import pywintypes
    ZBUS = connect_zbus(INTERFACE)
    RX6 = connect('RX6', INTERFACE)
    RZ5 = connect('RZ5', INTERFACE)
    # Merri: For a two-speaker configuration I believe you would want to do
    # something such as PA5_1 = connect('PA5', ID=1)
    PA5 = connect('PA5', INTERFACE)
except ImportError, e:
    log.exception('Missing module.  Unable to load hardware drivers')
except pywintypes.com_error, e:
    log.error('TDT ActiveX drivers are not registered.  Will not be ' + \
              'able to connect to the zBUS.')

def load(circuit, device):
    try:
        circuit = rpcox.circuit_factory(circuit, globals()[device])
        globals()[device+'_circuit'] = circuit
        return circuit
    except KeyError:
        raise SystemError, '%s not initialized' % device

def init_device(circuit, device, **kwargs):
    circuit = load(circuit, device)
    circuit.start(**kwargs)
    return circuit

def set_attenuation(atten, device):
    try:
        globals()[device].SetAtten(atten)
    except KeyError:
        raise SystemError, '%s not initialized' % device
