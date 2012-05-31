import tables
import numpy as np
from cns import h5

def rethreshold_extracted(ext_filename):
    '''
    Thresholding spike data is a time-intensive process.  If all you changed was
    the artifact threshold (in the raw physiology file), then you can simply
    recompute the artifact metadata, otherwise, you'll need to run the full
    extraction process.
    '''
    with tables.openFile(ext_filename, 'a') as fh:
        raw_filename = ext_filename.replace('extracted', 'raw')
        md = h5.p_read(raw_filename, '*/data/physiology/channel_metadata')
        channels = fh.root.event_data._v_attrs.extracted_channels-1

        rms = fh.root.event_data._v_attrs.noise_std
        rej_thresholds_std = md['artifact_std'][channels]
        rej_thresholds = rms * rej_thresholds_std
        rej_thresholds = rej_thresholds[..., np.newaxis]
        fh_waveforms = fh.root.event_data.waveforms
        exp = tables.Expr("(fh_waveforms >= rej_thresholds) |" 
                          "(fh_waveforms < -rej_thresholds)")
        artifacts = np.any(exp.eval(), axis=-1)

        # We can represent up to 256 values with an 8 bit integer.  That's overkill
        # for a boolean datatype; however Matlab doesn't support pure boolean
        # datatypes in a HDF5 file.  Lame.  Artifacts is a 2d array of [event,
        # channel] indicating, for each event, which channels exceeded the artifact
        # reject threshold.
        fh.root.event_data.artifacts._f_remove()
        node = fh.createCArray('/event_data', 'artifacts', tables.Int8Atom(),
                               shape=artifacts.shape, 
                               title='Artifact (event, channel)')

        fh.root.event_data._v_attrs['reject_threshold'] = rej_thresholds
        fh.root.event_data._v_attrs['reject_threshold_std'] = rej_thresholds_std
        node[:] = artifacts

if __name__ == '__main__':
    import argparse
    description = 'Recompute artifact thresholds'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Files to process')
    args = parser.parse_args()
    for ext_filename in args.files:
        rethreshold_extracted(ext_filename)
