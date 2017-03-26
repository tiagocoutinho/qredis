# QRedis

A [python][py], [Qt][qt] based [redis][redis] client user interface.

![qredis in action](doc/screen1.png)

## Installation

    $ pip install qredis

## Requirements

* [python][py] >= 2.6
* [PyQt][pyqt]\(4/5\) (or in the future PySide)
* [redis][redis-py]

## Usage

    $ qredis with no DB loaded on startup
    $ qredis

    $ connect to localhost:6379, db=0
    $ qredis -p 637

    $ connect with unix socket, db=5
    $ qredis -s /tmp/redis.sock -n 5

That's all folks!

[qt]: http://www.qt.io/
[py]: http://www.python.org/
[pyqt]: http://riverbankcomputing.com/software/pyqt
[redis]: http://redis.io
[redis-py]: https://github.com/andymccurdy/redis-py
