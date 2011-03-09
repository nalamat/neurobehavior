# Ensure that ETS toolkit will default to Qt4 if we load it
import os
os.environ['ETS_TOOLKIT'] = 'qt4' 

# Add the library folder for the branch
from os.path import abspath, dirname, join
import sys
libdir = abspath(join(dirname(__file__), '..'))
sys.path.insert(0, libdir)

import logging
from time import strftime
 
# Log detailed information to file
from cns import LOG_ROOT
filename = join(LOG_ROOT, strftime('%Y%m%d_%H%M.log'))
file_handler = logging.FileHandler(filename)
fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(fmt)
file_handler.setLevel(logging.DEBUG)
logging.root.addHandler(file_handler)

# Print pertinent information to console
console_handler = logging.StreamHandler()
fmt = logging.Formatter(fmt='%(levelname)s - %(name)s - %(message)s')
console_handler.setFormatter(fmt)
console_handler.setLevel(logging.DEBUG)
logging.root.addHandler(console_handler)

logging.root.setLevel(logging.DEBUG)
