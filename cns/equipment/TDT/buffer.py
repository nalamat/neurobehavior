from __future__ import division

log = logging.getLogger(__name__)

type_lookup = {
        np.float32: 'F32',
        np.int32:   'I32',
        np.int16:   'I16',
        np.int8:    'I8',
        }

'''
Many of these buffer functions rely on strict naming conventions to be able to
correctly download data from the DSP.  The conventions are as follows:

    Continuous acquire
        1) <buffer>             name of tag connected to data port of buffer
        2) <buffer>_idx         tag connected to index port of buffer
        Each time a read is requested, <buffer>_idx is checked to see if it has
        incremented since the last read.  If it has, the new data is acquired
        and returned.

    Triggered acquire
        1) <buffer>             name of tag connected to data port of buffer
        2) <buffer>_idx_trig    index of last sample buffer acquired prior to
                                the trigger
        Each time a read is requested, <buffer>_idx_trig is checked to see if it
        has changed since the last read.  If it has, the new data is
        acquired and returned.  This data should reflect the entire recording
        over a single trigger.

    Dual acquire
        <Not finished yet> I may not get around to this unless we need it
'''

@pipeline
def source(source, name, length=None, src_type=np.float32,
        dest_type=np.float32, channels=1, sf=1, read='continuous', multiple=1,
        compression=None):

    # TDT allows data to be stored as F32, I32, I16 or I8.  We look up the
    # appropriate parameters to pass to the ActiveX function that acquires the
    # data.
    read_func = source.dsp.ReadTagVEX
    args = type_lookup[src_type], type_lookup[dest_type], 1

    # The TDT buffers store in 4 byte format.  We need to determine the
    # compression ratio (i.e. int32 has only 2 bytes so the data is compressed
    # by a factor of 2).
    comp = 4/np.nbytes[src_type]

    if read == 'continuous': name_idx = name + '_idx'
    elif read == 'triggered': name_idx = name + '_idx_trig'
    else: raise ValueError, '%s read not supported' % read

    # Note that GetTagSize does not return the actual size of the buffer if the
    # size was changed from the default that is set in the RCX file (e.g. by
    # connecting the buffer size to a parameter tag and changing the value of
    # this tag via SetTagVal).  There really is no need to be changing buffer
    # size once the generator is started.  Early attempts to write the program
    # with dynamic buffer sizes were complicated, so I have stripped out this
    # functionality.  If you need to resize the buffer, you have to construct a
    # new generator.
    buffer_size = set_length(source, name, length)
    offset = getattr(source, name_idx).value

    mesg = 'Buffer %s opened for %s read using %s.  ' + \
            'Size %d, compression %d, shuffling %d, multiple %d'
    log.debug(mesg % \
            (name, read, name_idx, buffer_size, comp, channels, multiple))

    if comp == 1 and channels == 1:
        # Default loop for generic buffer read where there is no compression
        # (should be faster).
        while True:
            # Very important!  We must read name_idx only once and store it locally as
            # the DSP will continue to acquire data while we are doing our processing.
            # We simply will grab the current data up to the point at which we read
            # name_idx.
            new_offset = getattr(source, name_idx).value

            # Available reports the number of samples ready to be read and
            # accounts for various edge cases.  See function documentation for
            # more detail.
            read_size = available(offset, new_offset, buffer_size, multiple)
            if read_size == 0:
                yield np.array([])
            else:
                indices = wrap(offset, read_size, buffer_size)
                data = [read_func(name, o, l, *args)[0] for o, l in indices]

                # I really don't like this concatenate call as it requires
                # making a copy of the array.  We already know the exact size of
                # the buffer we are reading!
                yield np.concatenate(data)
                offset = new_offset

    else:
        # Loop for compression and shuffling with scaling.  Will run slower than
        # the above version.

        # Since two samples are compressed into a single word before being
        # shuffled, the data is stored in the order A1 A2 B1 B2 C1 C2 D1 D2 A3
        # A4 B3 B4 C3 C4 D3 D4 (where A through D are "channels" and 1 through 4
        # are the sample number).  We need to compensate for this by using some
        # fancy indexing.
        r = comp

        while True:
            new_offset = getattr(source, name_idx).value
            read_size = available(offset, new_offset, buffer_size, multiple)
            if read_size == 0:
                # We need to reshape the empty array to give it dimensionality
                # so that attempting to index a channel does not result in an
                # error.  For example, data[:,1] should give us [] for channel 1.
                yield np.array([]).reshape((-1, channels))
            else:
                indices = wrap(offset, read_size, buffer_size)

                # The TDT ActiveX documention does not appear to accurately
                # describe how ReadTagVEX works.  ReadTagVEX wants the number of
                # samples acquired, not the buffer index.  If two samples are
                # compressed into a single buffer slot, then we need to multiply
                # the read size by 2.  If four samples are compressed into a
                # single buffer slot, the read size needs to be 4.

                # We also need to offset the read appropriately.  <Don't fully
                # understand this but my test code says I've got it OK>
                data = [read_func(name, o*r, l*r, *args)[0] for o, l in indices]

                data = np.concatenate(data)/sf
                if channels<>1 and compression=='decimate':
                    # Do not change the four lines below unless you test it with
                    # timeit!  This has been optimized for speed.  See
                    # test_concatenate_time.py (in the same folder as this file)
                    # to see the test results.  This method is an order of a
                    # magnitude faster than any other method I have thought of.
                    temp = np.empty((len(data)/channels, channels))
                    for i in range(channels):
                        for j in range(comp):
                            temp[j::comp,i] = data[i*comp+j::comp*channels]
                    yield temp

                elif channels<>1:
                    data.shape = (-1, channels)
                    yield data
                else: yield data
                offset = new_offset

