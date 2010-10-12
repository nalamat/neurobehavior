import logging

from enthought.envisage.core_plugin import CorePlugin
from enthought.envisage.ui.workbench.workbench_plugin import WorkbenchPlugin

from acme.lorenz.lorenz_application import LorenzApplication
from acme.lorenz.lorenz_plugin import LorenzPlugin
from acme.lorenz.lorenz_ui_plugin import LorenzUIPlugin
from acme.lorenz.animal_plugin import AnimalPlugin


# Do whatever you want to do with log messages! Here we create a log file.
logger = logging.getLogger()
#logger.addHandler(logging.StreamHandler(file('lorenz.log', 'w')))
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

def main():
    """ Run the application. """

    # Create an application with the specified plugins.
    lorenz_application = LorenzApplication(
        plugins=[
            CorePlugin(), WorkbenchPlugin(), LorenzPlugin(), LorenzUIPlugin(),
            AnimalPlugin(),
        ]
    )

    lorenz_application.run()
    return

if __name__ == '__main__':
    main()
