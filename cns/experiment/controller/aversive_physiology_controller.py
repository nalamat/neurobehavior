'''
Created on May 10, 2010

@author: Brad
'''

from .aversive_controller import AversiveController
from cns import equipment
from cns.data.h5_utils import append_node
from cns.experiment.data.aversive_physiology_data import AversivePhysiologyData
from enthought.traits.api import Any, on_trait_change, Range, Instance
from datetime import datetime
import numpy as np
from cns.widgets.views.channel_view import MultiChannelView

