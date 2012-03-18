import numpy as np
import tables
from cns import h5

ts = lambda TTL: np.flatnonzero(TTL)
edge_rising = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == 1
edge_falling = lambda TTL: np.r_[0, np.diff(TTL.astype('i'))] == -1

def get_epochs(TTL):
    rising = ts(edge_rising(TTL))
    falling = ts(edge_falling(TTL))

    # This means that the TTL was high at the end of the experiment, resulting
    # in no falling edge.  Remove the very last rising edge.
    if (len(rising) > len(falling)) and TTL[-1] == 1:
        rising = rising[:-1]

    # This means that the TTL was high at the beginning of the experiment,
    # resulting in no rising edge.  Insert a rising edge at T=0.
    if (len(rising) < len(falling)) and TTL[0] == 1:
        rising = np.r_[0, rising]

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

            # Check to see if we have any continuous nose-pokes that triggered
            # more than one trial (these are not actually continuous nose-poke,
            # the sampling rate was so low that we simply did not detect the
            # discontinuity).  If so, we need to break down this nose-poke into
            # two nose-pokes.  We know that the subject broke the nose-poke
            # when the response window went high, so we'll simply insert a zero
            # into the correct place in the nose-poke TTL signal and rerun the
            # script.  
            double_mask = mask.sum(0) > 1
            if double_mask.any():
                for lb, ub in all_poke_epoch[double_mask]:
                    i = ts(edge_rising(data.contact.response_TTL[lb:ub]))
                    data.contact.poke_TTL[lb+i] = False
                    data.contact.all_poke_epoch._f_remove()
                print 'Updated poke_TTL.  Please rerun script.'
                return

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
                ts_end = data.trial_log.cols.ts_end[:]
                incomplete_response_ts = response_ts
                response_ts = np.empty(len(ts_end))

                # Find out which response_ts values are missing.  If no
                # response_ts is within 500 msec of the ts_end value, we know
                # that the response_ts is missing.
                delta = np.abs(incomplete_response_ts-ts_end[np.newaxis].T)
                # Boolean mask indicating which trials we have a valid
                # response_ts for.
                valid = np.any(delta < (0.5 * TTL_fs), 1)

                response_ts[valid] = incomplete_response_ts

                # The trials for which we don't have a valid response_ts based
                # on the response_TTL should be discarded due to a faulty spout
                # sensor.  So, let's just use the ts_end timestamp instead.  The
                # ts_end timestamp is sampled at the same fs as the
                # response_TTL, so no conversion is needed.
                response_ts[~valid] = ts_end[~valid]

            node = fh.createArray(data.contact, 'response_ts', response_ts)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created response_ts'
        else:
            print 'response_ts already exists'

        # The logic for this is slightly more complicated because early versions
        # of the appetitive dt paradigm set the signal duration to 0 for the
        # nogo.  This effectively means that there's no signal_TTL during these
        # nogos, so what is the "epoch" in this case?  I may work this out
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

        # If the ts data is present, it is more likely to be of a higher
        # resolution than the epoch data.
        if 'ts' not in data.physiology:
            timestamps = data.physiology.epoch[:,0]
            node = fh.createArray(data.physiology, 'ts', timestamps)
            node._v_attrs['fs'] = TTL_fs
            node._v_attrs['t0'] = 0
            print 'created physiology ts'
        else:
            print 'physiology ts already exists'

        # Make sure the node flavor is set to Numpy
        for series in ('contact/all_poke_epoch',
                       'contact/poke_epoch',
                       'contact/trial_epoch',
                       'contact/all_spout_epoch',
                       'contact/signal_epoch'
                       'contact/response_ts',
                       'physiology/epoch',
                       'physiology/ts'):
            try:
                node = h5.p_get_node(data, series)
                if node.flavor != 'numpy':
                    node.flavor = 'numpy'
                    print 'Updated node flavor for ', series
            except tables.NoSuchNodeError:
                pass

if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        print "processing", filename
        main(filename)
