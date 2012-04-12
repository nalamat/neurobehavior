import tables
from cns import h5

paths = (
    '*/data/trial_log',
    '*/data/contact/poke_epoch',
    '*/data/contact/response_ts',
    '*/data/contact/trial_epoch',
    '*/data/contact/signal_epoch',
    )

def main(filename, trials):
    with tables.openFile(filename, 'a') as fh:
        lengths = [len(h5.p_get_node(fh.root, p)) for p in paths]
        #print lengths

        # Make sure that each node has the same number of trials saved.  If not,
        # then we need to look at the file by hand to make sure that we are
        # removing the correct data.
        if len(set(lengths)) != 1:
            raise ValueError, 'unequal elements in each array'
        for path in paths:
            node = h5.p_get_node(fh.root, path)
            node.truncate(trials)

if __name__ == '__main__':
    import sys
    filename, trials = sys.argv[1:]
    main(filename, int(trials))
