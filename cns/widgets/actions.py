from cns.widgets import icons
from enthought.traits.ui.menu import Action, ToolBar

behavior_actions = [Action(name='Load Animal', action='load_animal',
                           enabled_when='cohort is None',
                           image=icons.animal),
                    Action(name='Apply', action='apply',
                           enabled_when='handler.state is "paused"',
                           image=icons.apply),
                    Action(name='Run', action='run',
                           enabled_when='handler.state is "halted"',
                           image=icons.run),
                    Action(name='Remind', action='remind',
                           enabled_when='handler.state is "paused"',
                           image=icons.remind),
                    Action(name='Pause', action='pause', enabled=False,
                           enabled_when='handler.state is "running"',
                           image=icons.pause),
                    Action(name='Resume', action='resume', enabled=False,
                           enabled_when='handler.state is "paused"',
                           image=icons.resume),
                    Action(name='Stop', action='stop',
                           enabled_when='handler.state is "running" ' + \
                                        'or handler.state is "paused"',
                           image=icons.stop),
                           ]

behavior_toolbar = ToolBar(*behavior_actions, show_tool_names=False)
