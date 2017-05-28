import tables
from cns import h5
import numpy as np

node_names = (
    'poke_epoch',
    'response_ts',
    'trial_epoch',
    'signal_epoch',
    )

def main(filename):
    with tables.openFile(filename, 'a') as fh:
        data = h5.p_get_node(fh.root, '*/data')
        #trial_start = data.trial_log.cols.start[:]

        poke_node = data.contact.poke_epoch
        poke_epoch = poke_node[:]/poke_node._v_attrs['fs']
        bad_epoch = np.flatnonzero((poke_epoch[:,1] - poke_epoch[:,0]) < 0)[0]

        ## First check
        #extra_trial = None
        #for i, (start, poke) in enumerate(zip(trial_start, poke_epoch[:,0])):
        #    if start-poke > 1.25:
        #        extra_trial = i
        #        break
        #extra_trial -= 1

        # Check for negative signals.  This seems to be an indicator the epoch
        # data is incorrect.
        #signal_node = data.contact.signal_epoch
        #signal_epoch = signal_node[:]/signal_node._v_attrs['fs']
        #print signal_epoch[:,1]-signal_epoch[:,0]
        ##print signal_epoch[383:387,1] - signal_epoch[383:387,0]
        #bad_epoch = np.flatnonzero((signal_epoch[:,1]-signal_epoch[:,0]) < 0)[0]

        print bad_epoch
        print divmod(poke_epoch[bad_epoch][1], 60.0)

        for node_name in node_names:
            node = data.contact._f_getChild(node_name)
            node._f_rename(node_name + '_old')
            values = np.delete(node[:], bad_epoch, axis=0)
            new_node = fh.createArray(data.contact, node_name, values)
            for attr in node._v_attrs._v_attrnamesuser:
                new_node._v_attrs[attr] = node._v_attrs[attr]

if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    main(filename)
