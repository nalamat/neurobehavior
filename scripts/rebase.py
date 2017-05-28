from os.path import dirname, abspath, join
import sys

module_path = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, module_path)
print "Added {} to the Python path".format(module_path)

sys.argv = sys.argv[1:]
execfile(sys.argv[0])
