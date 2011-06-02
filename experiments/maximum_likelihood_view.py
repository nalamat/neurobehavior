from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.chaco.api import *
from eval import ExpressionTrait
from maximum_likelihood import MaximumLikelihood
from enthought.enable.api import Component, ComponentEditor
import numpy as np

class MaximumLikelihoodSelector(HasTraits):

    def __init__(self, parameters=None):
        self.parameters = parameters
        self.finalize()

    def finalize(self):
        a = self.fa_rate.eval()
        m = self.midpoint.eval()
        k = self.slope.eval()
        self.tracker = MaximumLikelihood(a, m, k)
        self.finalized = True

    def next(self, sequence=None, response=None):
        if sequence is None:
            parameter = self.midpoint.eval().max()
        else:
            parameter = self.tracker.send(sequence, response)
        self.track.append(parameter)
        self.track_value.set_data(self.track)
        self.track_index.set_data(np.arange(len(self.track)))
        return { 'duration' : parameter }

    def _track_view_default(self):
        container = OverlayPlotContainer()
        scatter = ScatterPlot(self.track_index, self.track_value,
                marker='circle')
        container.add(scatter)
        return container
