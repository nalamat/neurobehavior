from __future__ import division

import sys

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

