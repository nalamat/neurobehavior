import tables

'''
Removes nodes from single-use files (e.g. files created using the -f command
line switch via load_experiment.py) that do not have a trial log attached to
them.  These nodes are typically experiments that were created then aborted
before a trial was initiated. 

Supports processing a list of filenames (hint, use a shell that supports
wildcard expansion).
'''

def main(filename):
    with tables.openFile(filename, 'a') as fh:
        for node in fh.root._f_iterNodes():
            if 'trial_log' not in node.data:
                print 'removing node', node
                node._f_remove(recursive=True)

if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        main(filename)
