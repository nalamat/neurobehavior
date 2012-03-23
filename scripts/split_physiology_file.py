import re
import tables 

def main(filename):
    with tables.openFile(filename, 'r') as fh:
        if fh.root._v_nchildren != 1:
            filename_pattern = re.sub(r'(.*)\.hd5', r'\1_v{}.hd5', filename)
            for i, node in enumerate(fh.root._f_listNodes()):
                new_filename = filename_pattern.format(i)
                with tables.openFile(new_filename, 'w') as fh_out:
                    print 'Moving {} to {}'.format(node._v_pathname,
                                                   new_filename)
                    node._f_copy(fh_out.root, recursive=True)
        else:
            print 'Only one experiment node in {}.  Skipping.'.format(filename)

if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        print 'Splitting {}'.format(filename)
        main(filename)
