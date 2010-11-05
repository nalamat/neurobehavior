from tables import *

# Define a user record to characterize some kind of particles
class Particle(IsDescription):
    name      = StringCol(16)   # 16-character String
    idnumber  = Int64Col()      # Signed 64-bit integer
    ADCcount  = UInt16Col()     # Unsigned short integer
    TDCcount  = UInt8Col()      # unsigned byte
    grid_i    = Int32Col()      # integer
    grid_j    = Int32Col()      # integer
    pressure  = Float32Col()    # float  (single-precision)
    energy    = FloatCol()      # double (double-precision)

filename = "test.h5"
# Open a file in "w"rite mode
h5file = openFile(filename, mode = "w", title = "Test file")
# Create a new group under "/" (root)
group = h5file.createGroup("/", 'detector', 'Detector information')
# Create one table on it
table = h5file.createTable(group, 'readout', Particle, "Readout example")
# Fill the table with 10 particles
particle = table.row
for i in xrange(10):
    particle['name']  = 'Particle: %6d' % (i)
    particle['TDCcount'] = i % 256
    particle['ADCcount'] = (i * 256) % (1 << 16)
    particle['grid_i'] = i
    particle['grid_j'] = 10 - i
    particle['pressure'] = float(i*i)
    particle['energy'] = float(particle['pressure'] ** 4)
    particle['idnumber'] = i * (2 ** 34)
    # Insert a new particle record
    particle.append()
# Close (and flush) the file
h5file.close()
