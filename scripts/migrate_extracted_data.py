import argparse
import tables
from glob import glob

blocks = (
    'physiology_epoch', 
    'poke_epoch',
    'trial_epoch',
    'trial_log',
    'physiology_ts',
    'signal_epoch',
    'all_poke_epoch',
    'response_ts',
)

filt_attrs = (
    'fc_highpass',
    'fc_lowpass',
    'filter_btype',
    'filter_order',
    'filter_padding',
    'chunk_loverlap',
    'chunk_roverlap',
)

fs_decorate = (
    'covariance_data',
    'timestamps',
    'waveforms'
)

extract_nodes = (
    'artifacts',
    'channel_indices',
    'channels',
    'covariance_data',
    'covariance_matrix',
    'timestamps',
    'waveforms'
)


extract_attrs = (
    'chunk_samples',
    'cross_time',
    'samples_after',
    'samples_before',
    'window_samples',
    'window_size',
)

extract_node_to_attrs = (
    'noise_std',
    'reject_threshold',
    'reject_threshold_std',
    'threshold',
    'threshold_std',
    'extracted_channels',
)

def main(filename):
    with tables.openFile(filename, 'a') as fh:
        try:
            filter_node = fh.root.filter
        except AttributeError:
            filter_node = fh.createGroup('/', 'filter')
        
        try:
            fh.root.filter_a._f_move(filter_node, 'a_coefficients')
        except AttributeError:
            pass

        try:
            fh.root.filter_b._f_move(filter_node, 'b_coefficients')
        except AttributeError:
            pass

        try:
            fh.root.differential._f_move(filter_node, 'differential')
        except AttributeError:
            pass


        for attr in filt_attrs:
            try:
                filter_node._v_attrs[attr] = fh.root._v_attrs[attr]
                del fh.root._v_attrs[attr]
            except:
                pass

        try:
            block_node = fh.root.block_data
        except AttributeError:
            block_node = fh.createGroup('/', 'block_data')

        for block in blocks:
            try:
                node = fh.root._f_getChild(block)
                node._f_move(block_node)
            except AttributeError:
                pass

        try:
            fh.root.bad_channels._f_move(filter_node)
        except AttributeError:
            pass

        try:
            event_node = fh.root.event_data
        except AttributeError:
            event_node = fh.createGroup('/', 'event_data')

        for node in extract_nodes:
            try:
                node = fh.root._f_getChild(node)
                node._f_move(event_node)
            except AttributeError:
                pass

        for attr in extract_attrs:
            try:
                event_node._v_attrs[attr] = fh.root._v_attrs[attr]
                del fh.root._v_attrs[attr]
            except:
                pass

        for name in extract_node_to_attrs:
            try:
                node = fh.root._f_getChild(name)
                event_node._v_attrs[name] = node[:]
                node._f_remove()
            except AttributeError:
                pass

        try:
            fs = fh.root._v_attrs['fs']
            for name in fs_decorate:
                try:
                    node = event_node._f_getChild(name)
                    node._v_attrs['fs'] = fs
                except AttributeError:
                    pass
            del fh.root._v_attrs['fs']
        except KeyError:
            pass

        if 'timestamps_n' not in event_node:
            node = event_node.timestamps
            node._f_rename('timestamps_n')
            ts = node[:] / node._v_attrs['fs']
            fh.createArray(event_node, 'timestamps', ts)

if __name__ == '__main__':
    class GlobPath(argparse.Action):

        def __call__(self, parser, args, values, option_string=None):
            filenames = []
            for filename in values:
                filenames.extend(glob(filename))
            setattr(args, self.dest, filenames)

    parser = argparse.ArgumentParser(description='Reformat extracted file')
    parser.add_argument('files',  nargs='+', action=GlobPath, 
                        help='Files to decimate')
    args = parser.parse_args()

    for filename in args.files:
        main(filename)
        print 'Processed {}'.format(filename)
