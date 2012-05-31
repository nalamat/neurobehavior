import tables
from cns import h5
from cns import analysis

def main(filename):
    '''
    Removes artifacts typically found at the beginning and end of an experiment
    (e.g. when putting the animal in the cage or when the headstage falls off at
    the end of the experiment).
    '''
    with tables.openFile(filename, 'a') as fh:
        exp_node = h5.p_get_node(fh, '*')
        start = exp_node.data.trial_log.cols.start[0] - 5
        end = exp_node.data.trial_log.cols.end[-1] + 5
        if start > 0:
            analysis.zero_waveform(exp_node, start)
        analysis.truncate_waveform(exp_node, end)

if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        print filename
        main(filename)
