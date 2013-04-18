import tables

def main(filename):
    with tables.openFile(filename, 'a') as fh:
        if 'diff_mode' in fh.root._v_attrs:
            fh.root.filter._v_attrs['diff_mode'] = fh.root._v_attrs['diff_mode']
            print 'Fixed diff mode for', filename

if __name__ == '__main__':
    import sys
    for filename in sys.argv[1:]:
        main(filename)
