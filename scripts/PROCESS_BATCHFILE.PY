from __future__ import division

import pickle
import tables
from os import path

from cns import analysis
from cns.io import update_progress

def main(batchfile, force_overwrite=False):
    '''
    Run jobs queued in a batchfile created by the physiology review program
    '''
    fh = open(batchfile, 'r')
    failed_jobs = []
    print 'Processing jobs in', batchfile
    with open(batchfile, 'rb') as fh:
        while True:
            try:
                fn, file_info, kwargs = pickle.load(fh)
                outfile = file_info['output_file']
                if path.exists(outfile) and not force_overwrite:
                    print 'Output file {} exists'.format(outfile)
                    failed_jobs.append((fn, file_info, kwargs))
                    continue

                # Open the source/destination for reading/writing as
                # appropriate
                fh_in = tables.openFile(file_info['input_file'], 'r',
                                        rootUEP=file_info['input_path'])
                fh_out = tables.openFile(file_info['output_file'], 'w',
                                         rootUEP=file_info['output_path'])

                # Update the list of keyword arguments to inclue the
                # additional arguments required
                kwargs['progress_callback'] = update_progress
                kwargs['input_node'] = fh_in.root
                kwargs['output_node'] = fh_out.root

                print 'Running {} on {}'.format(fn, file_info['input_file'])
                getattr(analysis, fn)(**kwargs)

                # Add a newline after the processing is done because the
                # progress callback does not insert a newline when plotting
                # the progressbar.
                print '\n'
                # Catch all other errors and queue failed jobs so we can
                # look at them later.  We want to continue processing the
                # rest of the jobs.
                #import traceback
                #traceback.print_exception(e)
                #print 'An exception occured'
                #print 'Skipping file', file_info['input_file']
                #failed_jobs.append((fn, file_info, kwargs))
                fh_in.close()
                fh_out.close()

            except EOFError:
                # This error is raised when pickle reaches the end of the file
                # and no more jobs are available
                break

    # Save failed jobs to file
    if failed_jobs:
        print "There were failed jobs.  Please see the failed_jobs.dat file."
        with open('failed_jobs.dat', 'wb') as fh:
            pickle.dump(failed_jobs, fh)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing output files')
    args = parser.parse_args()
    main(args.file, args.force_overwrite)
