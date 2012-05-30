import tables
import numpy as np
from cns.util.binary_funcs import epochs, smooth_epochs

def censor_spikes(ext_filename, rms_pad=0.5, block_pad=5, artifact_pad=0.5,
                  artifact_mode='single', force_overwrite=False):
    '''
    Censor extracted spikes based on three criteria::

        noise floor
        artifacts
        block

    Once the spikes have been censored, you can use the physiology review GUI
    (using the overla extracted spikes feature) to inspect the censored result.
    '''

    with tables.openFile(ext_filename, 'a') as fh:
        enode = fh.root.event_data

        if 'censored' in fh.root.event_data:
            if not force_overwrite:
                raise IOError, 'Censored data already exists'
            else:
                fh.root.event_data.censored._f_remove()
                fh.root.censor._f_remove(recursive=True)

        cnode = fh.createGroup('/', 'censor')
        censored = fh.createCArray(enode, 'censored', tables.BoolAtom(),
                                   enode.timestamps.shape)

        channel_indices = enode.channel_indices[:]

        lb = fh.root.block_data.trial_log.cols.start[0]-block_pad
        ub = fh.root.block_data.trial_log.cols.end[-1]+block_pad

        if artifact_mode == 'all':
            # Censor based on transients occuring on *any* channel
            artifact_mask = np.any(enode.artifacts[:], axis=-1)
            artifact_ts = enode.timestamps[artifact_mask]
            artifact_epochs = np.c_[artifact_ts-artifact_pad,
                                    artifact_ts+artifact_pad]
            artifact_epochs = smooth_epochs(artifact_epochs)

        for i, ch in enumerate(enode._v_attrs.extracted_channels-1):
            mask = i == channel_indices
            timestamps = enode.timestamps[mask]

            if np.diff(timestamps).min() < 0:
                raise ValueError, 'Timestamps are not ordered!'

            # Censor based on RMS artifacts
            rms = fh.root.rms.rms[ch]
            rms_th = np.median(rms)/0.6745
            #rms_mean = rms.mean()
            #rms_std = rms.std()
            #rms_th = rms_mean + rms_stdev*rms_std
            rms_epochs = epochs(rms >= rms_th, rms_pad)
            rms_epochs = rms_epochs / fh.root.rms.rms._v_attrs.fs
            rms_epochs = smooth_epochs(rms_epochs)

            j = np.searchsorted(rms_epochs[:,0], timestamps)
            k = np.searchsorted(rms_epochs[:,1], timestamps)
            rms_censor = ~(j == k) 

            # Censor based on block start/end
            block_censor = (timestamps < lb) | (timestamps > ub)

            if artifact_mode == 'single':
                # Censor based on transients in data.  Need to recompute this
                # for each channel.
                artifact = enode.artifacts[:,i][mask].astype('bool')
                artifact_ts = timestamps[artifact]
                artifact_epochs = np.c_[artifact_ts-artifact_pad,
                                        artifact_ts+artifact_pad]
                artifact_epochs = smooth_epochs(artifact_epochs)

            j = np.searchsorted(artifact_epochs[:,0], timestamps)
            k = np.searchsorted(artifact_epochs[:,1], timestamps)
            artifact_censor = ~(j == k) 

            # Update the censor mask
            censored[mask] = rms_censor | block_censor | artifact_censor

            # Save the censor data
            cenode = fh.createGroup(cnode, 'extracted_{}'.format(i))
            cenode._v_attrs['channel'] = ch+1 # 1-based channel number
            array = fh.createEArray(cenode, 'rms_epochs', shape=(0, 2),
                                    atom=tables.Float32Atom(),
                                    title='Censored RMS epochs')
            array.append(rms_epochs)
            array._v_attrs['rms_pad'] = rms_pad
            array._v_attrs['rms_threshold'] = rms_th

            # Save the artifact reject data
            array = fh.createEArray(cenode, 'artifact_epochs', shape=(0, 2),
                                    atom=tables.Float32Atom(),
                                    title='Censored artifact epochs')
            array.append(artifact_epochs)
            array._v_attrs['artifact_pad'] = artifact_pad
            array._v_attrs['artifact_mode'] = artifact_mode

            # Save the block reject data
            cenode._v_attrs['block_start'] = lb
            cenode._v_attrs['block_end'] = ub

            all_epochs = np.r_[[(0, lb)], 
                               rms_epochs, 
                               artifact_epochs, 
                               [(ub, np.inf)]]
            all_epochs.sort()
            all_epochs = smooth_epochs(all_epochs)
            fh.createArray(cenode, 'censored_epochs', all_epochs,
                           title='All censored epochs')

        # Save some metadata regarding the censoring process (this is redundant
        # with the data stored in the subnodes, but provided here as well)
        cnode._v_attrs['rms_pad'] = rms_pad
        cnode._v_attrs['block_pad'] = block_pad
        cnode._v_attrs['artifact_pad'] = artifact_pad
        cnode._v_attrs['artifact_mode'] = artifact_mode

if __name__ == '__main__':
    import argparse
    description = 'Censor spikes in extracted spiketimes file'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Files to process')
    parser.add_argument('--rms-pad', type=float, default=0.2, 
                        help='Padding for RMS')
    parser.add_argument('--block-pad', type=float, default=5.0, 
                        help='Padding for block')
    parser.add_argument('--artifact-pad', type=float, default=0.2, 
                        help='Padding for artifact')
    parser.add_argument('--artifact-mode', choices=('single', 'all'),
                        default='single', help='Reject mode')
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing censor data')

    args = parser.parse_args()
    for filename in args.files:
        print 'Processing file', filename
        try:
            censor_spikes(filename, 
                          rms_pad=args.rms_pad, 
                          block_pad=args.block_pad,
                          artifact_pad=args.artifact_pad,
                          artifact_mode=args.artifact_mode,
                          force_overwrite=args.force_overwrite)
        except IOError:
            print 'Censored data already exists, skipping file.'
