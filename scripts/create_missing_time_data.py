import numpy as np
import tables
from cns import h5

ts = lambda TTL: np.flatnonzero(TTL)
edge_rising = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == 1
edge_falling = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == -1

def get_epochs(TTL):
    rising = ts(edge_rising(TTL))
    falling = ts(edge_falling(TTL))
    if np.any(falling < rising):
        raise ValueError, "Unable to compute epoch"
    return np.c_[rising, falling]

def main(filename):
    '''
    Add the missing timeseries data:

        all_poke_epoch
        poke_epoch
        response_ts
        signal_epoch - not implemented
        trial_epoch

    Also creates some epoch data never seen before:

        all_spout_epoch
    '''
    with tables.openFile(filename, 'a') as fh:
        data = h5.p_get_node(fh.root, '*/data')
        TTL_fs = data.contact.poke_TTL._v_attrs['fs']
        trial_start = (data.trial_log.cols.start * TTL_fs).astype('i')
        trials = len(trial_start)

        if 'all_poke_epoch' not in data.contact:
            all_poke_epoch = get_epochs(data.contact.poke_TTL[:])
            node = fh.createArray(data.contact, 'all_poke_epoch',
                                  all_poke_epoch)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created all_poke_epoch'
        else:
            print 'all_poke_epoch already exists'

        if 'poke_epoch' not in data.contact:
            # If we are inside this statement, it is highly probable that we
            # already had to compute all_poke_epoch above.  Howver, just in case
            # we didn't, let's load it back in from the file.
            all_poke_epoch = data.contact.all_poke_epoch[:]

            # Use broadcasting to do away with a for loop and find out which
            # poke epochs bracket the start of a trial.
            trial_start = trial_start[np.newaxis].T
            mask = (all_poke_epoch[:,0] <= trial_start) & \
                   (all_poke_epoch[:,1] > trial_start)
            mask = mask.any(0)
            poke_epoch = all_poke_epoch[mask]
            if len(poke_epoch) != trials:
                raise ValueError, "Unable to winnow down poke epoch list"
            node = fh.createArray(data.contact, 'poke_epoch', poke_epoch)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created poke_epoch'
        else:
            print 'poke_epoch already exists'

        if 'response_ts' not in data.contact:
            response_ts = get_epochs(data.contact.response_TTL[:])[:,1]
            if len(response_ts) != trials:
                raise ValueError, 'Unable to compute response ts'
            node = fh.createArray(data.contact, 'response_ts', response_ts)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created response_ts'
        else:
            print 'response_ts already exists'

        # The logic for this is slightly more complicated because early versions
        # of the appetitive dt paradigm set the signal duration to 0 for the
        # nogo.  This effectively means that there's no signal_TTL during these
        # nogos, so what is the "epoch" in this case?  I will work this out
        # later.  I don't really use signal_epoch (we already know when the
        # signal is presented based on the trial start timestamp). 
        #
        #if 'signal_epoch' not in data.contact:
        #    signal_epoch = get_epochs(data.contact.signal_TTL[:])
        #    print len(signal_epoch), trials
        #    if len(signal_epoch) != trials:
        #        raise ValueError, 'Unable to compute signal epoch'
        #    node = fh.createArray(data.contact, 'signal_epoch', signal_epoch)
        #    node._v_attrs['fs'] = TTL_fs
        #    node._v_attrs['t0'] = 0

        if 'all_spout_epoch' not in data.contact:
            all_spout_epoch = get_epochs(data.contact.spout_TTL[:])
            node = fh.createArray(data.contact, 'all_spout_epoch',
                                  all_spout_epoch)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created all_spout_epoch'
        else:
            print 'all_spout_epoch already exists'

        if 'trial_epoch' not in data.contact:
            trial_epoch = zip(data.trial_log.cols.ts_start,
                              data.trial_log.cols.ts_end)
            if len(trial_epoch) != trials:
                raise ValueError, 'Unable to compute trial epoch'
            node = fh.createArray(data.contact, 'trial_epoch', trial_epoch)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created trial_epoch'
        else:
            print 'trial_epoch already exists'

        # Return from this function if there is no physiology data to work on
        if 'physiology' not in data:
            return

        if 'epoch' not in data.physiology:
            epoch = get_epochs(data.physiology.sweep[:])
            node = fh.createArray(data.physiology, 'epoch', epoch)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created physiology epoch'
        else:
            print 'physiology epoch already exists'

        # If the ts data is present, it is more likely to be of a
        # higher resolution than the epoch data.
        if 'ts' not in data.physiology:
            ts = data.physiology.epoch[:,0]
            node = fh.createArray(data.physiology, 'ts', ts)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created physiology ts'
        else:
            print 'physiology ts already exists'


if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        main(filename)
