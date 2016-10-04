from os.path import join
from cns import get_config
from cns.pipeline import deinterleave_bits
from abstract_experiment_controller import AbstractExperimentController
from abstract_experiment_controller import ExperimentToolBar
from traits.api import Any, Instance, Bool

from enable.savage.trait_defs.ui.svg_button import SVGButton

from traitsui.api import Item, View, HGroup, spring, VGroup
from cns.widgets.icons import icons

import win32api

class PositiveStage1ToolBar(ExperimentToolBar):

    size    = 24, 24
    kw      = dict(height=size[0], width=size[1], action=True)
    item_kw = dict(show_label=False)
    running = "object.handler.state=='running'"
    paused = "object.handler.state=='paused'"

    manual = SVGButton('Manual', filename=icons['pause'], tooltip='Manual control', **kw)
    automatic = SVGButton('Automatic', filename=icons['resume'], tooltip='Auto mode', **kw)
    main_group = HGroup(
        Item('apply', enabled_when="object.handler.pending_changes"),
        Item('revert', enabled_when="object.handler.pending_changes"),
        Item('start', enabled_when="object.handler.state=='halted'"),
        '_',
        Item('manual', enabled_when="object.handler.state=='running'", **item_kw),
        Item('automatic', enabled_when="object.handler.state=='paused'", **item_kw),
        Item('stop', enabled_when="object.handler.state in " + "['running', 'paused', 'manual']"),
        spring,
        springy=True,
        show_labels=False,
        )

    target_play   = SVGButton('Play Target'   , filename=icons['speaker'  ],
        tooltip='Play target sound' , **kw)
    masker_toggle = SVGButton('Toggle Masker' , filename=icons['speaker'  ],
        tooltip='Toggle masker sound', **kw)
    sound_group = VGroup(
        Item('target_play'   , enabled_when=paused, **item_kw),
        Item('masker_toggle' , enabled_when=paused, **item_kw),
        )

    pump_trigger2 = SVGButton('Trigger Pump' , filename=icons['water-blue'],
        tooltip='Trigger pump for reward volume', **kw)
    pump_toggle2  = SVGButton('Toggle Pump'  , filename=icons['water' ],
        tooltip='Toggle pump state'     , **kw)
    pump_group = VGroup(
        Item('pump_trigger2', enabled_when=paused, **item_kw),
        Item('pump_toggle2' , enabled_when=paused, **item_kw),
        )
    light_timeout = SVGButton('Timeout Light', filename=icons['light-off'  ],
        tooltip='Turn light off for the timeout period', **kw)
    light_toggle  = SVGButton('Toggle Light' , filename=icons['light-on'   ],
        tooltip='Toggle light'     , **kw)
    light_group = VGroup(
        Item('light_timeout', enabled_when=paused, **item_kw),
        Item('light_toggle' , enabled_when=paused, **item_kw),
        )

    traits_view = View(
        VGroup(
            main_group,
            HGroup(
                sound_group,
                pump_group,
                light_group,
                label='Manual Control',
                show_border=True,
                ),
            ),
        kind='subpanel')

class PositiveStage1Controller(AbstractExperimentController):

    pipeline_TTL = Any

    toolbar = Instance(PositiveStage1ToolBar, (), toolbar=True)

    def setup_experiment(self, info):
        log.error('Not implemented')

    def start_experiment(self, info):
        self.manual(self, info)

    def automatic(self, info=None):
        self.state = 'running'

    def manual(self, info=None):
        self.state = 'paused'

    def monitor_behavior(self):
        log.error('Not implemented')

    def get_ts(self):
        log.error('Not implemented')

    def _get_status(self):
        if self.state == 'halted':
            return "Halted"
        if self.state == 'paused':
            return "Experimenter controlled"
        else:
            return "Subject controlled"

    def context_updated(self):
        log.error('Not implemented')

    def update_waveform(self):
        log.error('Not implemented')
