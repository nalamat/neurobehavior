import argparse
from subprocess import call
import re
import tables 

def main(filename, dry_run=False):
    file_edited = False
    mode = 'r' if dry_run else 'a'
    with tables.openFile(filename, mode) as fh:
        for node in fh.root._f_listNodes():
            try:
                phys = node.data.physiology
                if dry_run:
                    print phys.processed._v_pathname
                    if 'raw' not in phys:
                        print 'WARNING >>> NO RAW DATA'
                else:
                    phys.processed._f_remove()
                for i in range(1, 17):
                    try:
                        if dry_run:
                            print getattr(phys, 'spike_{:02}'.format(i))._v_pathname
                            print getattr(phys, 'spike_{:02}_ts'.format(i))._v_pathname
                            print getattr(phys, 'spike_{:02}_classifier'.format(i))._v_pathname
                        else:
                            getattr(phys, 'spike_{:02}'.format(i))._f_remove()
                            getattr(phys, 'spike_{:02}_ts'.format(i))._f_remove()
                            getattr(phys, 'spike_{:02}_classifier'.format(i))._f_remove()
                    except AttributeError:
                        pass
                file_edited = True
            except Exception, e:
                print e
                pass
    if file_edited and not dry_run:
        print 'file edited'
        repack_filename = re.sub(r'(.*)\.hd5', r'\1_repack.hd5', filename)
        print call(['ptrepack', filename+':/', repack_filename+':/'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Strip redundant data from physiology files")
    parser.add_argument('files',  nargs='+', help='Files to simplify')
    parser.add_argument('--dry-run', action='store_true',
                        help="Show actions without modifying the file")
    args = parser.parse_args()

    for filename in args.files:
        print 'Processing', filename
        main(filename, args.dry_run)

