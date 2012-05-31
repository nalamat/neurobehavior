import tables
from os import path

from cns import io
from cns import analysis
from cns import h5

def extract_spikes(raw_filename, force_overwrite=False):
    '''
    Extract spikes from raw data based on information stored in the channel
    metadata table.  Use the review physiology GUI to configure and save the
    settings for spike extraction.
    '''
    ext_filename = raw_filename.replace('raw', 'extracted')
    if path.exists(ext_filename) and not force_overwrite:
        raise IOError, 'Extracted file already exists'

    kwargs = io.create_extract_arguments_from_raw(raw_filename)
    fh_in = tables.openFile(raw_filename, 'r')
    kwargs['input_node'] = h5.p_get_node(fh_in, '*') 
    fh_out = tables.openFile(ext_filename, 'w')
    kwargs['output_node'] = fh_out.root
    kwargs['progress_callback'] = io.update_progress
    analysis.extract_spikes(**kwargs)
    fh_in.close()
    fh_out.close()

if __name__ == '__main__':
    import argparse
    description = 'Extract spikes from raw data'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Files to process')
    parser.add_argument('--force-overwrite', default=False, 
                        help='Overwrite existing file?')

    args = parser.parse_args()
    for ext_filename in args.files:
        extract_spikes(ext_filename, args.force_overwrite)
