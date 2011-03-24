from physiology_data_mixin import PhysiologyDataMixin
from pump_data_mixin import PumpDataMixin

class AbstractExperimentData(PhysiologyDataMixin, PumpDataMixin):

    def channel_from_buffer(self, buffer, channel_name):
        channel_trait = self.trait(channel_name)
        klass = channel_trait.trait_type.klass
        factory = channel_trait.trait_type.find_klass(klass)
        store_path = channel_trait.store_path
        dtype = channel_trait.dtype

        path, name = store_path.split('/')
        node = get_or_append_node(self.store_node, path)
        channel = factory(channels=buffer.channels, fs=buffer.fs, node=node,
                name=name, dtype=dtype)

        setattr(self, channel_name, channel)
