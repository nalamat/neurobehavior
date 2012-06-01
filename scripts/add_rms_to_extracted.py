import tables
from cns import h5
from cns.io import update_progress
from cns.analysis import running_rms

def compute_rms(extracted_filename):
    '''
    Add running measurement of RMS noise floor to the extracted spiketimes file.
    This metric is required for many of the spike processing routines; however,
    this is such a slow (possibly inefficient) algorithm that it was broken out
    into a separate function.
    '''
    processing = {}
    with tables.openFile(extracted_filename, 'a') as fh:
        raw_filename = extracted_filename.replace('extracted', 'raw')

        if 'rms' in fh.root:
            fs = fh.root.rms.rms._v_attrs['fs']
            last_trial = fh.root.block_data.trial_log.cols.end[-1]
            dur = fh.root.rms.rms.shape[-1]/fs
            mesg = 'Already has RMS of duration {}.  Last trial ends at {}.'
            print mesg.format(dur, last_trial)
            return

        processing['filter_freq_lp'] = fh.root.filter._v_attrs.fc_lowpass
        processing['filter_freq_hp'] = fh.root.filter._v_attrs.fc_highpass
        processing['filter_order'] = fh.root.filter._v_attrs.filter_order
        processing['filter_btype'] = fh.root.filter._v_attrs.filter_btype
        processing['bad_channels'] = fh.root.filter.bad_channels[:]-1
        processing['diff_mode'] = fh.root.filter._v_attrs.diff_mode

        with tables.openFile(raw_filename, 'r') as fh_raw:
            input_node = h5.p_get_node(fh_raw.root, '*')
            output_node = fh.createGroup('/', 'rms')
            running_rms(input_node, output_node, 1, 0.25, processing=processing,
                        algorithm='median', progress_callback=update_progress)

if __name__ == '__main__':
    import argparse
    description = 'Add RMS to extracted spiketimes file'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Files to procss')
    parser.add_argument('--stdev', type=float, default=2, 
                        help='Threshold for RMS')
    args = parser.parse_args()
    for filename in args.files:
        print 'Processing file', filename
        try:
            compute_rms(filename)
        except Exception as e:
            print e
