from add_rms_to_extracted import compute_rms

import tables
from os import path

from cns import io
from cns import analysis
from cns import h5

def extract_spikes(raw_filename, template=None, force_overwrite=False):
    '''
    Extract spikes from raw data based on information stored in the channel
    metadata table.  Use the review physiology GUI to configure and save the
    settings for spike extraction.
    '''
    ext_filename = raw_filename.replace('raw', 'extracted')
    if path.exists(ext_filename) and not force_overwrite:
        raise IOError, 'Extracted file already exists'

    if template is None:
        kwargs = io.create_extract_arguments_from_raw(raw_filename)
    elif 'extracted' in template:
        kwargs = io.create_extract_arguments_from_extracted(template)
    elif 'raw' in template:
        kwargs = io.create_extract_arguments_from_raw(template)
    else:
        raise ValueError, 'Unsupported template'

    fh_in = tables.openFile(raw_filename, 'r')
    kwargs['input_node'] = h5.p_get_node(fh_in, '*') 
    fh_out = tables.openFile(ext_filename, 'w')
    kwargs['output_node'] = fh_out.root
    kwargs['progress_callback'] = io.update_progress
    analysis.extract_spikes(**kwargs)
    fh_in.close()
    fh_out.close()
    return ext_filename

if __name__ == '__main__':
    import argparse
    description = 'Extract spikes from raw data'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Raw files to process')
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing file')
    parser.add_argument('--add-rms', action='store_true', help='Add RMS to file')
    parser.add_argument('--template', help='Use settings defined in this file')

    args = parser.parse_args()
    for raw_filename in args.files:
        ext_filename = extract_spikes(raw_filename, 
                                      template=args.template,
                                      force_overwrite=args.force_overwrite)
        if args.add_rms:
            compute_rms(ext_filename)
