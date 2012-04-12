import tables
from cns import h5
import numpy as np

def main(filename):
    '''
    Validate timeseries data

        poke_epoch
        response_ts
        signal_epoch - not implemented
        trial_epoch
    '''
    with tables.openFile(filename, 'r') as fh:
        data = h5.p_get_node(fh.root, '*/data')
        trial_start = data.trial_log.cols.start[:]
        trial_end = data.trial_log.cols.end[:]
        
        poke_node = data.contact.poke_epoch
        poke_epoch = poke_node[:]/poke_node._v_attrs['fs']

        # Make sure that all poke starts are before the start of the trial
        try:
            if not np.all(poke_epoch[:,0] < trial_start):
                raise ValueError, 'poke epoch'
            # Make sure that all pokes occured within 1 second of the trial start
            if not np.all((poke_epoch[:,0]-trial_start) < 1.25):
                raise ValueError, 'poke epoch'
            # Make sure that the end of the poke did not occur before the start of
            # the next trial
            if not np.all(poke_epoch[:-1,1] < trial_start[1:]):
                print poke_epoch[:-1,1] < trial_start[1:]
                raise ValueError, 'poke epoch'
        except ValueError:
            trials = len(trial_start)
            dt = poke_epoch[:trials,0]-trial_start
            print np.flatnonzero(dt < -2)[0]
            raise

        response = data.contact.response_ts
        response_ts = response[:]/response._v_attrs['fs']
        fs_error = data.contact.response_TTL._v_attrs['fs']**-1

        if not np.all(response_ts > trial_start):
            print np.flatnonzero(~(response_ts > trial_start))[0]
            raise ValueError, 'response ts'
        if not np.all(response_ts <= (trial_end+2*fs_error)):
            print fs_error
            print response_ts-(trial_end+fs_error)
            raise ValueError, 'response ts'

if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        print "processing", filename
        main(filename)
