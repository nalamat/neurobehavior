import numpy as np
from os import path
import dt
import tables
from mne.time_frequency import tfr
from cns.util.binary_funcs import epochs_contain
from cns import h5

def compute_spectra(dec_filename, frequencies, lb=-2.0, ub=1.5,
                    reference='trial_start'):

    def _process_and_save(spectra, group):

        if 'total_power' not in group:
            # Shape shall be format [channel, frequency, time]
            shape = np.r_[0, spectra.shape[1:]]
            fh.createEArray(group, 'total_power', tables.atom.Float64Atom(),
                            shape=shape, expectedrows=16)
            fh.createEArray(group, 'total_power_std', tables.atom.Float64Atom(),
                            shape=shape, expectedrows=16)
            fh.createEArray(group, 'evoked_power', tables.atom.Float64Atom(),
                            shape=shape, expectedrows=16)
            fh.createEArray(group, 'phase_lock', tables.atom.Float64Atom(),
                            shape=shape, expectedrows=16)
            fh.createEArray(group, 'phase', tables.atom.Float64Atom(),
                            shape=shape, expectedrows=16)

        total_power = np.mean(np.abs(spectra)**2, 0)
        total_power_std = np.std(np.abs(spectra)**2, 0)
        evoked_power = np.mean(spectra, 0)*np.mean(np.conj(spectra), 0)
        evoked_power = np.real(evoked_power)
        phase = spectra/np.abs(spectra)
        phase_lock = np.abs(np.mean(phase, 0))
        phase = np.mean(np.angle(phase), 0)

        group.total_power.append(total_power[np.newaxis])
        group.total_power_std.append(total_power_std[np.newaxis])
        group.evoked_power.append(evoked_power[np.newaxis])
        group.phase_lock.append(phase_lock[np.newaxis])
        group.phase.append(phase[np.newaxis])

    raw_filename = dec_filename.replace('dec', 'raw')
    ext_filename = raw_filename.replace('raw', 'extracted')
    tl = dt.load_trial_log(raw_filename)
    spec_filename = dec_filename.replace('dec.hd5', reference + '_spec.hd5')
    
    if path.exists(spec_filename):
        raise IOError, 'Filename already exists'

    try:
        # If available, exclude the censored data
        ts = tl[reference]
        c_epochs = dt.censored_epochs(ext_filename)
        mask = epochs_contain(c_epochs, ts+lb) | epochs_contain(c_epochs, ts+ub)
        tl = tl[~mask]
    except:
        pass

    with tables.openFile(dec_filename) as fh:
        fs = fh.root.lfp._v_attrs.fs
        lfp = dt.get_waves(fh.root.lfp, tl[reference], lb, ub)

    tl['array_index'] = np.arange(len(tl))

    # Look up the the good channels and only process these
    md = h5.p_read(raw_filename, '*/data/physiology/channel_metadata')
    channels = md['index'][~md['bad']] # 0-based index

    print lfp.shape
    print channels
    print spec_filename

    with tables.openFile(spec_filename, 'w') as fh:
        fh.root._v_attrs['fs'] = fs
        fh.root._v_attrs['lb'] = lb
        fh.root._v_attrs['ub'] = ub
        fh.root._v_attrs['frequencies'] = frequencies
        fh.root._v_attrs['morlet_cycles'] = 3

        ga_group = fh.createGroup('/', 'grand_average')
        ga_group._v_attrs['n'] = len(tl)

        for channel in channels:
            print 'Computing spectra for channel {}'.format(channel+1)
            spectra = tfr.cwt_morlet(lfp[:,channel,:], fs, frequencies,
                                     use_fft=False, n_cycles=3, zero_mean=True)

            _process_and_save(spectra, ga_group)

            for level, l_frame in tl.groupby('level'):
                key = '{}'.format(level)

                if key not in fh.root:
                    group = fh.createGroup('/', key)
                    group._v_attrs['n'] = len(l_frame)
                else:
                    group = fh.root._f_getChild(key)
                _process_and_save(spectra[l_frame.array_index], group)

                for yes, r_frame in l_frame.groupby('yes'):
                    label = 'yes' if yes else 'no'
                    key = '{}_{}'.format(label, level)
                    if key not in fh.root:
                        group = fh.createGroup('/', key)
                        group._v_attrs['n'] = len(r_frame)
                    else:
                        group = fh.root._f_getChild(key)
                    _process_and_save(spectra[r_frame.array_index], group)

    print 'done saving'

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compute spectrogram')
    parser.add_argument('files',  nargs='+', help='Decimated files to process')
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing output files')
    parser.add_argument('--reference', type=str)
    args = parser.parse_args()
    frequencies = 2**np.arange(1, 8.1, .2)

    for filename in args.files:
        try:
            print 'Processing ', filename
            compute_spectra(filename, frequencies, -2, 1.5)
        except Exception as e:
            print e
