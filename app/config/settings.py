import os
os.environ['ETS_TOOLKIT'] = 'qt4' # can be either WX or QT4.  QT4 has a better
                                  # SVG renderer.
from os.path import abspath, dirname, join
import sys

libdir = abspath(join(dirname(__file__), '../..'))
sys.path.insert(0, libdir)

log_config = join(dirname(abspath(__file__)), "logging.conf")
import logging.config
logger = logging.config.fileConfig(log_config)
