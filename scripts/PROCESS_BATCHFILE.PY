from __future__ import division

import sys
import pickle
import tables
from cns import analysis

def update_progress(i, n, mesg):
    '''
    Command-line progress bar.
    '''
    max_chars = 60
    progress = i/n
    num_chars = int(progress*max_chars)
    num_left = max_chars-num_chars
    # The \r tells the cursor to return to the beginning of the line rather than
    # starting a new line.  This allows us to have a progressbar-style display
    # in the console window.
    sys.stdout.write('\r[{}{}] {:.2f}%'.format('#'*num_chars, 
                                               ' '*num_left,
                                               progress*100))
    return False

def process_batchfile(batchfile):
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

                # Open the source/destination for reading/writing as appropriate
                fh_in = tables.openFile(file_info['input_file'], 'r',
                                        rootUEP=file_info['input_path'])
                fh_out = tables.openFile(file_info['output_file'], 'a',
                                         rootUEP=file_info['output_path'])

                # Update the list of keyword arguments to inclue the additional
                # arguments required
                kwargs['progress_callback'] = update_progress
                kwargs['input_node'] = fh_in.root
                kwargs['output_node'] = fh_out.root

                print 'Running {} on {}'.format(fn, file_info['input_file'])
                getattr(analysis, fn)(**kwargs)
            except EOFError:
                # This error is raised when pickle reaches the end of the file
                # and no more jobs are available
                break
            except Exception, e:
                # Catch all other errors and queue failed jobs so we can look at
                # them later.  We want to continue processing the rest of the
                # jobs.
                print 'An exception occured', e
                failed_jobs.append((fn, file_info, kwargs))
            finally:
                fh_in.close()
                fh_out.close()

    # Save failed jobs to file
    if failed_jobs:
        print "There were failed jobs.  Please see the failed_jobs.dat file."
        with open('failed_jobs.dat', 'wb') as fh:
            pickle.dump(failed_jobs, fh)

if __name__ == '__main__':
    process_batchfile(sys.argv[1])
