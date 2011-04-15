import os

FILE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
STYLE = 'oxygen'
SIZE = 'scalable'

RESOURCE_PATH = os.path.join(FILE_DIRECTORY, 'resource/', STYLE, SIZE)

oxygen_icons = {'start':        'actions/1rightarrow.svgz',
                'warn':         'actions/messagebox_warning.svg',
                'stop':         'actions/stop.svgz',
                'apply':        'actions/system_run.svgz',
                'pause':        'actions/player_pause.svgz',
                'resume':       'actions/player_play.svgz',
                'configure':    'actions/configure_toolbars.svg',
                'add':          'actions/plus.svg',
                'delete':       'actions/remove.svgz',
                'undo':         'actions/undo.svgz',
                'up':           'actions/go-up.svgz',
                'down':         'actions/go-down.svgz',
                'right2':       'actions/2rightarrow.svgz',
                'left2':        'actions/2leftarrow.svgz',
                }

for k, v in globals()[STYLE+'_icons'].items():
    globals()[k] = os.path.join(RESOURCE_PATH, v)
