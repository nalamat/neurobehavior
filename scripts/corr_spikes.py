from __future__ import division

import tables
import numpy as np

def common(a, b, window):
    a = np.asarray(a)
    b = np.asarray(b)
    indices = np.searchsorted(a, b)

    m = len(a)
    n = 0
    for i, ts in zip(indices, b):
        if (a[i-1]-window) <= ts < (a[i-1]+window):
            n += 1
        elif i < m and (a[i]-window) <= ts < (a[i]+window):
            n += 1
    return n

def corr_spikes(ext_filename, window=0.0005, force_overwrite=False):
    '''
    Pair-wise correlations (% of spikes that are likely the same spike)
    '''
    with tables.openFile(ext_filename, 'a') as fh:
        if 'common_events' in fh.root.event_data:
            if not force_overwrite:
                raise IOError, 'File already processed'
            else:
                fh.root.event_data.common_events._f_remove()

        extracted_channels = fh.root.event_data._v_attrs.extracted_channels
        ts = fh.root.event_data.timestamps[:]
        channels = fh.root.event_data.channels[:]

        ch_ts = [ts[channels == ch] for ch in extracted_channels]

        n = len(extracted_channels)
        x = np.zeros((n, n))

        # Compute
        for i in range(n):
            for j in range(i+1, n):
                ts_a = ch_ts[i]
                ts_b = ch_ts[j]
                x[i, j] = 100*common(ts_a, ts_b, window)/len(ts_b)
                #x[i, j] = 32.1

        # Print
        print '\t' + '\t'.join(str(e) for e in extracted_channels)
        print ''
        for i in range(n):
            print extracted_channels[i], '\t', 
            for j in range(i):
                print '\t',
            print '-\t',
            for j in range(i+1, n):
                print str(int(x[i, j])), '\t',
            print ''

        # Save
        fh.createArray(fh.root.event_data, 'common_events', x, 
                       title='Percent of events shared by each channel')

if __name__ == '__main__':
    import argparse
    description = 'Show number of potential collisions'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('files', nargs='+', help='Files to process')
    parser.add_argument('--window', type=float, default=0.0005,
                        help='Window to compare')
    parser.add_argument('--force-overwrite', action='store_true',
                        help='Overwrite existing data')

    args = parser.parse_args()
    for ext_filename in args.files:
        print 'Processing file', ext_filename
        corr_spikes(ext_filename, window=args.window,
                    force_overwrite=args.force_overwrite)
