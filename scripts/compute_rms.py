from os import path
import re
import tables

import argparse

from cns.analysis import running_rms
from cns.io import update_progress

def main(infile, force_overwrite=False):
    fh_in = tables.openFile(infile, 'r')
    if fh_in.root._g_getnchildren() == 1:
        print 'Processing {}'.format(infile)
        outfile = re.sub(r'(.*)_raw\.hd5', r'\1_rms.hd5', infile)
        if path.exists(outfile) and not force_overwrite:
            raise IOError, '{} already exists'.format(outfile)
        fh_out = tables.openFile(outfile, 'w')
        output_node = fh_out.root
        input_node = fh_in.root._f_listNodes()[0]
        bad_channels = [0, 1, 2, 7]
        processing = dict(freq_hp=300, filter_btype='highpass',
                          bad_channels=bad_channels, diff_mode='all good')
        running_rms(input_node, output_node, 1, 1,
                    progress_callback=update_progress, processing=processing,
                    algorithm='median', chunk_size=10e6)
        fh_out.close()
        fh_in.close()
    else:
        mesg = "Unable to process {}".format(infile)
        raise ValueError, mesg

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Decimate files')
    parser.add_argument('files',  nargs='+', help='Files to decimate')
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing output files')
    args = parser.parse_args()

    for filename in args.files:
        main(filename, args.force_overwrite)
