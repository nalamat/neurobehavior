'''
Since it's possible for the user to abort spike extraction and still produce a
valid file, this script can be used to quickly scan a directory and determine
whether the *_extracted.hd5 files were generated using the full dataset.
'''

import tables
import re
import sys
from os import path
from glob import glob

def main(raw_filename, extracted_filename):
    fh_raw = tables.openFile(raw_filename, 'r')
    fh_ext = tables.openFile(extracted_filename, 'r')
    tl = fh_raw.root._f_listNodes()[0].data.trial_log
    last_trial = tl.read(field='end').max()
    ts = fh_ext.root.event_data.timestamps[-1]
    if ts < last_trial:
        print 'Error in ', extracted_filename
    try:
        fh_ext.root.event_data.covariance_matrix
    except AttributeError:
        print 'Error in ', extracted_filename
    fh_raw.close()
    fh_ext.close()

if __name__ == '__main__':
    directory = sys.argv[1]
    directory = path.join(directory, '*_extracted.hd5')
    for extracted_filename in glob(directory):
        raw_filename = re.sub(r'(.*)_extracted.hd5', r'\1.hd5',
                              extracted_filename)
        print raw_filename
        main(raw_filename, extracted_filename)
