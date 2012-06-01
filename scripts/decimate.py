from os import path
#import re
import tables

from cns.analysis import decimate_waveform
from cns.io import update_progress

def main(infile, dec_fs=600, outfile_suffix='dec', force_overwrite=False):
    fh_in = tables.openFile(infile, 'r')
    if fh_in.root._g_getnchildren() == 1:
        print 'Processing {}'.format(infile)
        outfile = infile.replace('raw', outfile_suffix)
        if path.exists(outfile) and not force_overwrite:
            raise IOError, '{} already exists'.format(outfile)
        fh_out = tables.openFile(outfile, 'w')
        output_node = fh_out.root
        input_node = fh_in.root._f_listNodes()[0]
        decimate_waveform(input_node, output_node, dec_fs=dec_fs,
                          progress_callback=update_progress)
        fh_out.close()
        fh_in.close()
    else:
        mesg = "Unable to process {}".format(infile)
        raise ValueError, mesg

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Decimate files')
    parser.add_argument('files',  nargs='+', help='Files to decimate')
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing output files')
    parser.add_argument('--dec-fs', type=float, default=600.0, 
                        help='Target decimation frequency')
    parser.add_argument('--outfile-suffix', type=str, default='dec')
    args = parser.parse_args()

    for filename in args.files:
        try:
            main(filename, args.dec_fs, args.outfile_suffix,
                 args.force_overwrite)
        except Exception, e:
            print e
