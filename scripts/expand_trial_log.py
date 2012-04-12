import tables
from cns import h5

def main(filename):
    with tables.openFile(filename, 'a') as fh:
        data = h5.p_load_node(fh.root, '*/data')
        tl = pandas.DataFrame(data.trial_log.read())

if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        main(filename)
