QRedis
======

A Python_, Qt_ based Redis_ client user interface.

.. image:: doc/screen1.png

Help wanted
-----------

Open to people who want to colaborate.

- Would like to know which features you would like to have
- Pull requests are welcome
- You can always open an issue saying you want to be part of the team

Installation
------------

::

    $ pip install qredis

Requirements
------------

- Python_ >= 2.6
- PyQt_ (4/5) (or in the future PySide)
- redis-py_

Usage
-----

::

    $ qredis with no DB loaded on startup
    $ qredis

    $ connect to localhost:6379, db=0
    $ qredis -p 6379

    $ connect with unix socket, db=5
    $ qredis -s /tmp/redis.sock -n 5


**That's all folks!**


.. _Qt: http://www.qt.io/
.. _Python: http://www.python.org/
.. _PyQt: http://riverbankcomputing.com/software/pyqt
.. _redis: http://redis.io
.. _redis-py: https://github.com/andymccurdy/redis-py
