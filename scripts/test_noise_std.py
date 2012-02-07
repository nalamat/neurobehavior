import numpy as np
from extract_spikes import noise_std
import tables
from cns.channel import ProcessedFileMultiChannel 

if __name__ == '__main__':
    filename = 'c:/users/brad/desktop/110911_tail_behavior.hd5'
    fh = tables.openFile(filename, 'r')
    raw = fh.root.PositiveDTCLExperiment_2011_09_11_21_33_30.data.physiology.raw
    fs = raw._v_attrs['fs']
    #durations = [1, 2, 4, 8, 16, 32, 64, 128]
    #offsets = np.arange(10)*60*5
    offsets = [0]
    durations = [16]

    raw = ProcessedFileMultiChannel.from_node(raw, 
                                              diff_mode='all good',
                                              filter_pass='highpass',
                                              freq_hp=300,
                                              freq_lp=6000,
                                              filter_order=8,
                                              bad_channels=[7,13,14,15])

    std_stds = []
    times = []
    for offset in offsets:
        lb = int(fs*offset)
        offset_stds = []
        for duration in durations:
            samples = int(fs*duration)
            std = noise_std(raw[:,lb:lb+samples])
            offset_stds.append(std)
        std_stds.append(offset_stds)

