import tables

def strip_rms(extracted_filename):
    '''
    Strips the RMS node from the extracted spikes file (you probably won't need
    this as BNB created this for debugging purposes).
    '''
    with tables.openFile(extracted_filename, 'a') as fh:
        if 'rms' not in fh.root:
            raise IOError, 'Nothing to strip'
        fh.root.rms._f_remove(recursive=True)

if __name__ == '__main__':
    import argparse
    description = 'Strip RMS from extracted spikes file'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Files to compute RMS for')
    args = parser.parse_args()
    for filename in args.files:
        print 'Processing file', filename
        try:
            strip_rms(filename)
        except Exception as e:
            print e
