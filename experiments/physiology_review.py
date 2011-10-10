import tables
from .physiology_data import PhysiologyData
from .physiology_experiment import PhysiologyExperiment
from enthought.traits.ui.api import Controller

#with tables.openFile('d:/experiments/data/BNB/110827_middle_behavior_TBSI.hd5',
#                     'r') as fin:
#with tables.openFile('d:/experiments/data/GvT/GvT_TailF_260811_wireless_AM.hd5',
#                     'r') as fin:
with tables.openFile('d:/TBSI_TailF.hd5', 'r') as fin:
    #store_node = fin.root.PositiveDTExperiment_duration_attenuation_reward_volume_2011_08_27_19_22_49.data.physiology
    #store_node = fin.root.PositiveAMNoiseExperiment_modulation_depth_2011_08_26_18_04_51.data.physiology
    store_node = fin.root.BasicCharacterizationExperiment__2011_08_29_17_56_47.data.physiology
    #rint store_node
    data = PhysiologyData(store_node=store_node)
    PhysiologyExperiment(data=data).configure_traits(handler=Controller())
