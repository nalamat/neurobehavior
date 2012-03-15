if __name__ == '__main__':
    import re
    import tables 
    import sys
    from os import path
    from glob import glob
    pathname = sys.argv[1]
    globpattern = path.join(pathname, '*.hd5')
    for filename in glob(globpattern):
        with tables.openFile(filename, 'r') as fh:
            if fh.root._v_nchildren != 1:
                filename_pattern = re.sub(r'(.*)\.hd5', r'\1_v{}.hd5', filename)
                for i, node in enumerate(fh.root._f_listNodes()):
                    new_filename = filename_pattern.format(i)
                    with tables.openFile(new_filename, 'w') as fh_out:
                        node._f_copy(fh_out.root, recursive=True)
