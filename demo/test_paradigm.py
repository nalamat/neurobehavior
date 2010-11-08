import numpy as np
from cns.data import Animal
from cns.paradigm import *
from cns.paradigm.paradigm import *
from cns.paradigm.paradigm_view import *
from datetime import date
import tables

data.contact.send(np.ones(100e3))

data.update(0.5, 10, 'REMIND')
data.update(0.5, 10, 'REMIND')
data.update(0.5, 10, 'SAFE')
data.update(0.5, 10, 'SAFE')
data.update(0.5, 10, 'WARN')
data.update(0.5, 20, 'SAFE')
data.update(0.5, 20, 'SAFE')
data.update(0.5, 20, 'SAFE')
data.update(0.5, 20, 'WARN')
data.update(0.5, 20, 'SAFE')
data.update(0.5, 20, 'SAFE')
data.update(0.5, 20, 'SAFE')
data.update(0.5, 20, 'REMIND')
data.update(0.5, 20, 'WARN')

paradigm = Paradigm()
par_view = ParadigmView(paradigm=paradigm)
analyzed = AnalyzedTrialData(data=data)
view = AnalyzedTrialDataView(analyzed=analyzed)

#handler = ParadigmEquipmentHandler(paradigm=paradigm, data=data,
#        analyzed_data=analyzed)
#
view.configure_traits()
#ControllerView(analyzed_view=view, paradigm_view=par_view).configure_traits()
