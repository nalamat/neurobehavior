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

    if template is None:
        template = raw_filename
    kwargs = io.create_extract_arguments(template)

    if path.exists(ext_filename):
        if not force_overwrite:
            raise IOError, 'Extracted file already exists'
        else:
            ext_kwargs = io.create_extract_arguments(ext_filename)

            # Remove the extracted data information in preparation for the
            # reprocessing of the file.
            fh_out = tables.openFile(ext_filename, 'a')
            fh_out.root.event_data._f_remove(recursive=True)
            fh_out.root.filter._f_remove(recursive=True)
            fh_out.root.block_data._f_remove(recursive=True)
            fh_out.root.censor._f_remove(recursive=True)

            # Check to see if the filtering or referencing data has changed.  If
            # not, we can keep the RMS data stored in the extracted file
            # otherwise we need to discard that data and start fresh.
            if ext_kwargs['processing'] != kwargs['processing']:
                fh_out.root.rms._f_remove(recursive=True)
    else:
        print 'Discarding RMS data'
        fh_out = tables.openFile(ext_filename, 'w')

    fh_in = tables.openFile(raw_filename, 'r')
    kwargs['input_node'] = h5.p_get_node(fh_in, '*') 
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
    parser.add_argument('--skip-missing', action='store_true',
                        help='Skip file if channel metadata missing')

    args = parser.parse_args()
    for raw_filename in args.files:
        try:
            ext_filename = extract_spikes(raw_filename, 
                                          template=args.template,
                                          force_overwrite=args.force_overwrite)
            if args.add_rms:
                compute_rms(ext_filename)
        except:
            if not args.skip_missing:
                raise
