import tables
from cns import h5
from cns.io import update_progress
from cns.analysis import running_rms

def compute_rms(ext_filename, force_overwrite=False):
    '''
    Add running measurement of RMS noise floor to the extracted spiketimes file.
    This metric is required for many of the spike processing routines; however,
    this is such a slow (possibly inefficient) algorithm that it was broken out
    into a separate function.
    '''
    processing = {}
    with tables.openFile(ext_filename, 'a') as fh:
        raw_filename = ext_filename.replace('extracted', 'raw')

        if 'rms' in fh.root:
            if not force_overwrite:
                raise IOError, 'Already contains RMS data'
            else:
                fh.root.rms._f_remove(recursive=True)

        processing['filter_freq_lp'] = fh.root.filter._v_attrs.fc_lowpass
        processing['filter_freq_hp'] = fh.root.filter._v_attrs.fc_highpass
        processing['filter_order'] = fh.root.filter._v_attrs.filter_order
        processing['filter_btype'] = fh.root.filter._v_attrs.filter_btype
        processing['bad_channels'] = fh.root.filter.bad_channels[:]-1
        processing['diff_mode'] = fh.root.filter._v_attrs.diff_mode
        #channels = fh.root.event_data._v_attrs.extracted_channels[:]-1

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
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing RMS data')
    args = parser.parse_args()
    for filename in args.files:
        print 'Processing file', filename
        try:
            compute_rms(filename, args.force_overwrite)
        except IOError as e:
            print e
