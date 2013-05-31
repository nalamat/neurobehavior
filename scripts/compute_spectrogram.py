from __future__ import division

import warnings
warnings.simplefilter('ignore')

import numpy as np
from os import path
import dt
import tables
from mne.time_frequency import tfr
from cns.util.binary_funcs import epochs_contain
from cns import h5

import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

def compute_spectra(dec_filename, frequencies, lb=-2.0, ub=1.5,
                    decimation_factor=4, reference='trial_start',
                    force_overwrite=False):

    def _process_and_save(spectra, group):

        if 'total_power' not in group:
            log.debug('Creating nodes for the data')

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

        log.debug('Computing total power')
        p_spec = np.abs(spectra)**2
        total_power = np.mean(p_spec, 0)
        total_power_std = np.std(p_spec, 0)

        log.debug('Computing evoked power')
        evoked_power = np.mean(spectra, 0)*np.mean(np.conj(spectra), 0)
        evoked_power = np.real(evoked_power)

        log.debug('Computing phase')
        phase = spectra/np.abs(spectra)
        phase_lock = np.abs(np.mean(phase, 0))
        phase = np.mean(np.angle(phase), 0)

        log.debug('Saving the data')
        group.total_power.append(total_power[np.newaxis])
        group.total_power_std.append(total_power_std[np.newaxis])
        group.evoked_power.append(evoked_power[np.newaxis])
        group.phase_lock.append(phase_lock[np.newaxis])
        group.phase.append(phase[np.newaxis])

    raw_filename = dec_filename.replace('dec', 'raw')
    ext_filename = raw_filename.replace('raw', 'extracted')
    tl = dt.load_trial_log(raw_filename)
    spec_filename = dec_filename.replace('dec.hd5', reference + '_spec.hd5')
    
    if path.exists(spec_filename) and not force_overwrite:
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

    # Look up the the good channels and only process these
    md = h5.p_read(raw_filename, '*/data/physiology/channel_metadata')
    channels = md['index'][~md['bad']] # 0-based index

    with tables.openFile(spec_filename, 'w') as fh:
        fh.root._v_attrs['lfp_fs'] = fs
        fh.root._v_attrs['spec_fs'] = fs/decimation_factor
        fh.root._v_attrs['decimation_factor'] = decimation_factor
        fh.root._v_attrs['lb'] = lb
        fh.root._v_attrs['ub'] = ub
        fh.root._v_attrs['frequencies'] = frequencies
        fh.root._v_attrs['morlet_cycles'] = 3

        ga_group = fh.createGroup('/', 'grand_average')
        ga_group._v_attrs['n'] = len(tl)

        for channel in channels:
            log.debug('Computing spectra for channel %d', channel+1)
            waveforms = lfp[:,channel,:]
            reject = waveforms.max(-1) > 0.001
            spectra = tfr.cwt_morlet(waveforms[~reject], fs, frequencies,
                                     use_fft=False, n_cycles=3, zero_mean=True)
            log.debug('Spectra shape: %r', spectra.shape)
            spectra = spectra[..., ::decimation_factor]
            log.debug('Spectra shape after decimating: %r', spectra.shape)

            log.debug('Computing ensemble averages for spectra')

            fh.root._v_attrs['n_reject_{}'.format(channel)] = np.sum(reject)
            _process_and_save(spectra, ga_group)

            sub_tl = tl[~reject]
            sub_tl['array_index'] = np.arange(len(sub_tl))

            group = 'duration', 'fc', 'level'
            for (duration, fc, level), l_frame in sub_tl.groupby(group):
                key = '{}_{}_{}'.format(duration, fc, level)
                log.debug('Processing %s', key)

                if key not in fh.root:
                    group = fh.createGroup('/', key)
                    group._v_attrs['n'] = len(l_frame)
                else:
                    group = fh.root._f_getChild(key)
                _process_and_save(spectra[l_frame.array_index], group)
                group._v_attrs['trial_log_index'] = l_frame.index

                for yes, r_frame in l_frame.groupby('yes'):
                    label = 'yes' if yes else 'no'
                    key = '{}_{}_{}_{}'.format(duration, fc, level, label)
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
    #frequencies = 2**np.arange(1, 8.1, .2)
    frequencies = 2**np.arange(1, 8.5, 0.3)

    import glob
    files = glob.glob('n:/data/dt/phys_behavior/good_behavior/*_dec.hd5')

    for filename in files:
        print 'Processing ', filename
        try:
            compute_spectra(filename, frequencies, -1.5, 1.5,
            reference='poke_start',
            force_overwrite=args.force_overwrite)
        except Exception as e:
            print e

    for filename in files:
        print 'Processing ', filename
        try:
            compute_spectra(filename, frequencies, -1.5, 1.5,
            reference='trial_start',
            force_overwrite=args.force_overwrite)
        except Exception as e:
            print e
