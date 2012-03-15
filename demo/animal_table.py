from cns.data.ui.cohort import CohortView
from cns.data.type import Cohort, Animal
from datetime import date, timedelta

birth = date.today()-timedelta(days=30)

animals = [Animal(parents='HH', identifier='tail', birth=birth, sex='F'),
	   Animal(parents='HH', identifier='fluffy', birth=birth, sex='M'),
	   Animal(parents='UU', identifier='blue', birth=date.today()),
	  ]

cohort = Cohort(description='Control Group 1', animals=animals)
CohortView(cohort=cohort).configure_traits(view='edit_view')
