from itertools import count

def read_digital_lines(task, size=1):
    nlines = ctypes.c_uint32()
    mx.DAQmxGetDINumLines(task, '', nlines)
    nsamp = ctypes.c_int32()
    nbytes = ctypes.c_int32()
    data = np.empty((size, nlines.value), dtype=np.uint8)
    mx.DAQmxReadDigitalLines(task, size, 0, mx.DAQmx_Val_GroupByChannel, data,
                             data.size, nsamp, nbytes, None)
    return data.T


def constant_lookup(value):
    for name in dir(mx.DAQmxConstants):
        if name in mx.DAQmxConstants.constant_list:
            if getattr(mx.DAQmxConstants, name) == value:
                return name
    raise ValueError('Constant {} does not exist'.format(value))


def channel_info(channels, channel_type):
    task = create_task('channel_info_{}'.format(channel_type))
    if channel_type in ('di', 'do', 'digital'):
        mx.DAQmxCreateDIChan(task, channels, '', mx.DAQmx_Val_ChanPerLine)
    elif channel_type == 'ao':
        mx.DAQmxCreateAOVoltageChan(task, channels, '', -10, 10,
                                    mx.DAQmx_Val_Volts, '')
    elif channel_type == 'ai':
        mx.DAQmxCreateAIVoltageChan(task, channels, '',
                                    mx.DAQmx_Val_Cfg_Default, -10, 10,
                                    mx.DAQmx_Val_Volts, '')

    channels = ctypes.create_string_buffer('', 4096)
    mx.DAQmxGetTaskChannels(task, channels, len(channels))
    devices = ctypes.create_string_buffer('', 4096)
    mx.DAQmxGetTaskDevices(task, devices, len(devices))
    mx.DAQmxClearTask(task)

    return {
        'channels': [c.strip() for c in channels.value.split(',')],
        'devices': [d.strip() for d in devices.value.split(',')],
    }

def gen():
    for i in range(0, 10, 1):
        yield i

# print 'First run'
for i in (x*x for x in gen()):
    print i
    print i*2

""" hello
dfasdf

"""

# print 'Second run'
# for i in gen():
#     print i
