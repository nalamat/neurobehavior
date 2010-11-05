import os
os.environ['ETS_TOOLKIT'] = 'qt4' 
from os.path import abspath, dirname, join
import sys

libdir = abspath(join(dirname(__file__), '../..'))
sys.path.insert(0, libdir)

log_config = join(dirname(abspath(__file__)), "logging.conf")
import logging.config
logging.config.fileConfig(log_config)
