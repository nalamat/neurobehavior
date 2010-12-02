import logging
log = logging.getLogger(__name__)
import numpy as np

from .. import EquipmentError

'''The simplest way to connect to the TDT DSP devices is:

from cns import equipment
circuit = equipment.dsp().connect(circuit_name, device_name)

This returns an object that allows you to query and set variables in the DSP
code (i.e. "tags" as the TDT documentation refers to them) as well as read and
write access to the buffers.  See rpcox.py for more information.
'''

INTERFACE = 'GB'

DATA_TYPES = {
        68:     np.ndarray,     # Data buffer
        73:     int,            # integer
        74:     None,           # May indicate static parameter
        76:     bool,           # Logical value
        80:     np.ndarray,     # Coefficient buffer
        83:     float,          # Float
        65:     None,           # Undefined (e.g. unknown output) 
        }

from ..convert import P_UNIT, convert 

def get_tags(dsp, device):
    for tdt_type, python_type in DATA_TYPES.items():
        value = dsp.GetNextTag(device, tdt_type, 1)
        if value != '':
            yield value, python_type
            while True:
                value = dsp.GetNextTag(device, tdt_type, 0)
                if value != '':
                    yield value, python_type
                else:
                    break

def launch_openproject(project_name):
    '''
    Launch OpenProject and load the specified project

    If OpenProject or one of its components (OpenController, OpenEx, etc.) are
    already running, they will be closed.

    Be sure that settings are configured properly in cns.settings so that we can
    find the OpenProject binary and default path for all OpenProject files.
    '''
    from cns import settings
    import subprocess
    cmd = "{0} {1}/{2}/{2}.wsp".format(settings.OPENPROJECT_BINARY,
                                       settings.OPENPROJECT_PATH,
                                       project_name)
    return subprocess.Popen(cmd)

class Tag(object):
    '''
    Wrapper around a RPvdsEx circuit tag
    
    Arguments
    ---------
    name : string
        Name of the tag as defined in the RPvds circuit
    device : :class:`Device`
        The device running the RPvds circuit the tag is associated with

    Optional Arguments
    ------------------
    tag_type : type (default None)
        Type of tag.  When tag is accessed, it will be coerced to this type.  If
        None, no type coercion is performed.
    
    If you follow appropriate naming conventions in the DSP circuit, the get and
    set methods will be able to convert the provided value to the appropriate
    type.  For example, if the DSP tag expects number of samples (i.e. cycles of the
    DSP clock), the tag name must end in '_n'.

    >>> tag_n.set(3, src_unit='s')

    The value will then be multiplied by the DSP clock frequency and converted
    to the nearest integer before being sent to the DSP.

    To do the conversion yourself.

    >>> value = int(tag_n.dsp.fs*3)
    >>> tag_n.value = value

    Alternatively, if you do not provide a src_unit (i.e. source unit), no
    conversion is done to the value.

    >>> tag_n.set(value)

    Likewise, `Tag.get` supports units using the req_unit parameter (i.e.
    requested unit).  

    >>> tag_n.get(req_unit='s')
    '''

    def _get_fs(self):
        return self.device.fs

    fs = property(_get_fs)

    def _get_iface(self):
        return self.device.project.iface

    iface = property(_get_iface)

    def _get_target_name(self):
        return '{0}.{1}'.format(self.device.name, self.name)

    target_name = property(_get_target_name)

    def __init__(self, name, device, tag_type=None):
        self.name = name
        self.device = device
        self.tag_type = tag_type

        try:
            self.unit, = P_UNIT.match(name).groups()
        except AttributeError:
            self.unit = None

    def _get_value(self):
        return self.iface.GetTargetVal(self.target_name)

    def _set_value(self, value):
        if not self.iface.SetTargetVal(self.target_name, value):
            mesg = "Could not set value to %r" % value
            raise HardwareError(self.target_name, mesg)
        log.debug("Set %s to %r", self, value)

    value = property(_get_value, _set_value)

    def __repr__(self):
        return "<%s>" % self.target_name

    def set(self, value, src_unit=None):
        '''
        Convert value and upload to target

        Parameters
        ----------
        value : number
            Value to convert
        src_unit : str
            Unit of value
        '''
        if src_unit is not None:
            value = convert(src_unit, self.unit, value, self.fs)
        self.value = value

    def get(self, req_unit=None):
        if req_unit is not None:
            return convert(self.unit, req_unit, self.value, self.fs)
        else:
            return self.value

class Device(object):
    '''
    Represents a device associated with a project.  Contains utilities for
    communicating with the device.  Device tags are attributes of the instance.

    Parameters
    ----------
    project : :class:`Project`
        Instance of the project the device is associated with
    name : string
        Name of device as described in the project
    '''

    def __init__(self, project, name):
        self.project = project
        self.name = name

        for tag_name, tag_type in get_tags(self.iface, self.name):
            tag = Tag(tag_name, self, tag_type)
            # Python attribute names cannot contain ~ or % so we convert them to
            # an underscore.
            attr_name = tag_name.replace('~', '_').replace('%', '_')
            setattr(self, attr_name, tag)

    def _get_fs(self):
        return self.project.iface.GetSamplingSF(self.name)

    fs = property(_get_fs)

    def _get_iface(self):
        return self.project.iface

    iface = property(_get_iface)

    # Status codes from OpenDeveloper manual
    # Bit   Value   Status
    # 0     1       connected
    # 1     2       COF loaded
    # 2     4       circuit running

    def _get_status(self):
        return self.project.iface.GetDeviceStatus(self.name)

    _status = property(_get_status)

    def _is_connected(self):
        return self._status&1 != 0

    def _is_loaded(self):
        return self._status&2 != 0

    def _is_running(self):
        return self._status&4 != 0

    connected = property(_is_connected)
    loaded = property(_is_loaded)
    running = property(_is_running)

class Project(object):
    '''
    Represents a single OpenProject and contains utilities for loading and
    communicating with the project. 

    Technically this should be a singleton (i.e. only one instance can ever be
    created); however this is not enforced for now.

    When an instance is created, the OpenProject binary is launched with the
    desired project.

    Parameters
    ----------
    project_name : string
        The name of the project.  Assumes that the project file can be found
        at cns.settings.OPENPROJECT_PATH/project_name/project_name.wsp.
    device_names : list
        The names of the devices available (OpenDeveloper does not provide a way
        to query the avaliable device names, but once the names are provided we
        can determine what tags are available on each device).  The names *must*
        correspond to the devices defined in the OpenProject file (i.e. if you
        call the RZ5 "physiology" in the OpenProject file, you must pass the
        name "physiology" rather than "RZ5".
    '''

    # Status code map and its reverse (so we can look up the code either way)
    STATUS_CODES = {0: 'IDLE', 1: 'STANDBY', 2: 'PREVIEW', 3: 'RECORD'}
    INV_STATUS_CODES = dict((v,k) for k, v in STATUS_CODES.iteritems())

    def __init__(self, project_name, device_names):
        from actxobjects import TDevAccX
        self.iface = TDevAccX.TDevAccX()
        self.project_name = project_name
        self.process = launch_openproject(project_name)

        # This is likely difficult to recover from and usually will mean that
        # the user had an instance of OpenProject or one of its components
        # running.

        # Give the project a bit of time to launch.  Try reconnecting at
        # periodic intervals.
        import time
        retries = 0
        while True: 
            # Returns 1 on success
            if self.iface.ConnectServer('Local'):
                break
            retries +=1
            log.debug('OpenProject donnection attempt %d failed', retries)
            if retries == 5: # Give up
                mesg = "Unable to connect to local OpenProject server"
                raise EquipmentError("OpenEx", mesg)
            time.sleep(2)
        
        # Now that we have successfully connected, let's register an atexit hook
        # so we can successfully disconnect.
        import atexit
        atexit.register(self._disconnect)

        # Attach the devices to the project so we can access them as attributes
        for device_name in device_names:
            setattr(self, device_name, Device(self, device_name))

    def _disconnect(self):
        self.iface.CloseConnection()  # Close connection to OpenProject
        #self.process.terminate()      # Is this safe?

    def _get_mode(self):
        status_code = self.iface.GetSysMode()
        return self.STATUS_CODES[status_code]

    def _set_mode(self, mode):
        status_code = self.INV_STATUS_CODES[mode]
        if not self.iface.SetSysMode(status_code):
            raise HardwareError(self.name, 
                    'Unable to set mode to %s' % mode)

    mode = property(_get_mode, _set_mode)
