.. _getting_started:

===============
Getting Started
===============

.. _installation:

Installation and Upgrade
------------------------

If you want to use the TinyOlap package only, without the samples, then you need to install it using pip:

.. code-block:: console

   (.venv) $ pip install tinyolap

To upgrade to the latest version of TinyOlap you need to call

.. code-block:: console

   (.venv) $ pip install --upgrade tinyolap


Testing The Installation
------------------------

To test the installation, create a new python script, enter the following code and run the script.
If it does not through an error, then the TinyOalp package should have been installed properly.

.. code-block:: Python

    from tinyolap.database import Database
    # define your data space
    db = Database("tiny")

Exploring the Capabilities of TinyOlap
--------------------------------------

The easiest way to get started is to explore and run the various samples available in
the `sample folder of the GitHub project <https://github.com/Zeutschler/tinyolap/tree/main/samples>`_.

Further information about the samples can be found in the `online documentation <https://tinyolap.com/docs/getting_started.html>`_.