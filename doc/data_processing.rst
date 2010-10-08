Channel
=======

.. automodule:: cns.channel
    :members:

Pipeline
========

Generators and Coroutines
-------------------------
The code in :module:`cns.pipeline` uses generators and coroutines, which are a
feature not commonly used in programming languages.  While effort is made to
avoid using more arcane features of Python, coroutines are extremely useful in
the context of real-time data processing and visualization.  Coroutines can be
thought of as "pipelines" (hence the name of the module) that continuously
recieve data.  Once enough data is buffered, the algorithm is run and processed
data is removed from the buffer and passed to the next target.

Before attempting to understand the code here, I suggest you review an advanced
tutorial on coroutines_ and `PEP 342`_.

.. _coroutines: http://www.dabeaz.com/coroutines/
.. _`PEP 342`: http://www.python.org/dev/peps/pep-0342/

Note that these functions fall into two categories.  Pipelines and sources.
Sources generate data, pipelines consume data.

.. automodule:: cns.pipeline
    :members:
