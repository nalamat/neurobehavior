if __name__ == '__main__':
    from subprocess import call
    import re
    import tables 
    import sys
    from os import path
    from glob import glob
    pathname = sys.argv[1]
    globpattern = path.join(pathname, '*.hd5')
    #keep = ('epoch', 'raw', 'ts', 'sweep')
    for filename in glob(globpattern):
        print filename
        file_edited = False
        with tables.openFile(filename, 'a') as fh:
            for node in fh.root._f_listNodes():
                try:
                    phys = node.data.physiology
                    phys.processed._f_remove()
                    #print phys.processed._v_pathname
                    for i in range(1, 17):
                        getattr(phys, 'spike_{:02}'.format(i))._f_remove()
                        getattr(phys, 'spike_{:02}_ts'.format(i))._f_remove()
                        getattr(phys, 'spike_{:02}_classifier'.format(i))._f_remove()
                        #print getattr(phys, 'spike_{:02}'.format(i))._v_pathname
                        #print getattr(phys, 'spike_{:02}_ts'.format(i))._v_pathname
                        #print getattr(phys, 'spike_{:02}_classifier'.format(i))._v_pathname
                    file_edited = True
                except Exception, e:
                    print e
                    pass
        if file_edited:
            print 'file edited'
            repack_filename = re.sub(r'(.*)\.hd5', r'\1_repack.hd5', filename)
            print call(['ptrepack', filename+':/', repack_filename+':/'])
