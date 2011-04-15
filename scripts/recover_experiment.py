def recover_experiment(filename):
    from cns.data.h5_utils import walk_nodes
    import tables
    import textwrap
    f = tables.openFile(filename, 'r')
    for node in f.walkNodes():
        if node._v_name.startswith('aversive_'):
            if not hasattr(node.Data, 'Analyzed'):
                mesg = '''
                %s appears to be missing an analyzed set of data.
                This may be due to the program crashing.  Would you like an
                analysis to be run on this? (yes/no): 
                '''
                mesg = textwrap.dedent(mesg).replace('\n', ' ')
                ans = raw_input(mesg % node._v_pathname)
                print ans

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Analyze crashed experiment')
    parser.add_argument('file', type=str, nargs=1)
    op = parser.parse_args()
    recover_experiment(op.file[0])
