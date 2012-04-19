import tables
from cns import h5
from cns.io import update_progress
from cns.analysis import running_rms

def main(extracted_filename):
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
        processing['bad_channels'] = fh.root.filter.bad_channels[:]
        processing['diff_mode'] = fh.root.filter._v_attrs.diff_mode


        with tables.openFile(raw_filename, 'r') as fh_raw:
            input_node = h5.p_get_node(fh_raw.root, '*')
            output_node = fh.createGroup('/', 'rms')
            running_rms(input_node, output_node, 1, 0.25, processing=processing,
                        algorithm='median', progress_callback=update_progress)

if __name__ == '__main__':
    import argparse
    description = 'Add RMS to extracted spikes file'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Files to compute RMS for')
    args = parser.parse_args()
    for filename in args.files:
        print 'Processing file', filename
        try:
            main(filename)
        except Exception as e:
            print e
            pass
