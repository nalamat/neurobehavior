import numpy as np
import sys
import tables
from cns.analysis import load_trial_log
from cns.plottools import AxesIterator
import pylab
from os import path

import matplotlib as mp
mp.rcParams['figure.facecolor'] = 'white'
mp.rcParams['figure.figsize'] = 11, 8.5
mp.rcParams['figure.subplot.wspace'] = 0.4
mp.rcParams['font.size'] = 7
mp.rcParams['axes.titlesize'] = 10
mp.rcParams['axes.labelsize'] = 8
mp.rcParams['xtick.direction'] = 'out'
mp.rcParams['xtick.labelsize'] = 6
mp.rcParams['xtick.major.size'] = 2
mp.rcParams['xtick.major.pad'] = 2
mp.rcParams['ytick.direction'] = 'out'
mp.rcParams['ytick.labelsize'] = 6
mp.rcParams['ytick.major.size'] = 2
mp.rcParams['ytick.major.pad'] = 2

from scipy import signal

if __name__ == '__main__':
    filename, ch, lb, ub, reference = sys.argv[1:]
    ch = int(ch)-1
    lb = float(lb)
    ub = float(ub)
    with tables.openFile(filename, 'r') as fh:
        lfp = fh.root.lfp[ch]
        lfp_fs = fh.root.lfp._v_attrs['fs']
        tl = load_trial_log(filename, '/block_data')

        # Lowpass filter the signal
        b, a = signal.iirfilter(4, 300/(0.5*lfp_fs), btype='lowpass')
        lfp = signal.filtfilt(b, a, lfp)

        fig = pylab.figure()

        for ax, (level, df) in AxesIterator(tl.groupby('level')):
            ts = df[reference]
            lb_ts = np.floor((ts+lb) * lfp_fs).astype('i')
            ub_ts = lb_ts + int(lfp_fs * (ub-lb))
            waves = [lfp[l:u] for l, u in zip(lb_ts, ub_ts)]
            waves = np.vstack(waves)
            wave_mean = waves.mean(0)
            wave_std = waves.std(0)
            t = np.arange(wave_mean.shape[-1], dtype='f')/lfp_fs+lb
            ax.plot(t, wave_mean, 'k')
            ax.fill_between(t, wave_mean+wave_std, wave_mean-wave_std,
                            edgecolor='none', facecolor='0.5')
            ax.axis(xmin=lb, xmax=ub)
            ax.set_title('{} dB SPL'.format(level))

        fig.suptitle('Channel {} referenced to {} ({})'.format((ch+1),
                                                               reference,
                                                               path.basename(filename)))

    pylab.show()
