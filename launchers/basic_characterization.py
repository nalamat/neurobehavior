from enthought.traits.api import Instance
from enthought.traits.ui.api import View, Include, VSplit, VGroup, Item
from enthought.enable.api import Component, ComponentEditor
from cns.channel import FileChannel
from enthought.chaco.api import DataRange1D, LinearMapper
from cns.chaco_exts.rms_channel_plot import RMSChannelPlot


from experiments import (
        # Controller and mixins
        BasicCharacterizationController,
        BasicCharacterizationParadigm,
        AbstractExperiment,
        AbstractExperimentData,
        )

class Controller(BasicCharacterizationController): pass
class Paradigm(BasicCharacterizationParadigm): pass
class Experiment(AbstractExperiment):

    def _add_experiment_plots(self, index_mapper, container, alpha=0.25):
        value_range = DataRange1D(low_setting=-20, high_setting=80)
        value_mapper = LinearMapper(range=value_range)
        plot = RMSChannelPlot(channel=self.data.microphone,
                index_mapper=index_mapper, value_mapper=value_mapper,
                line_color=(0.2, 0.2, 0.2, 0.50))
        container.add(plot)

    traits_group = VGroup(
            Item('handler.toolbar', style='custom'),
            Item('paradigm', style='custom'),
            show_labels=False,
            )

class Data(AbstractExperimentData):

    microphone = Instance(FileChannel, store='channel', store_path='microphone')

    def _microphone_default(self):
        return FileChannel(node=self.store_node, name='microphone',
                dtype='float32')

node_name = 'BasicCharacterizationExperiment'
