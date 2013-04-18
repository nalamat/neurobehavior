from os import path

FILE_DIRECTORY = path.dirname(path.abspath(__file__))
RESOURCE_PATH = path.join(FILE_DIRECTORY, 'resource', 'oxygen', 'scalable')

icons = {'start':        'actions/1rightarrow.svgz',
         'warn':         'actions/messagebox_warning.svg',
         'stop':         'actions/stop.svgz',
         'apply':        'actions/system_run.svgz',
         'apply_now':    'actions/system_restart.svgz',
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

# Update the icon list with the full path to the resource
for k, v in icons.items():
    icons[k] = path.join(RESOURCE_PATH, v)
