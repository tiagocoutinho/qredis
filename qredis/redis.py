import collections

from redis import Redis, ConnectionError

from .util import KeyItem
from .qt import QObject, Signal


def _set(redis, key, value):
    redis.set(key, value)


def _set_list(redis, key, lst):
    redis.delete(key)
    redis.rpush(key, *lst)


def _set_set(redis, key, st):
    redis.delete(key)
    redis.sadd(key, *tuple(st))


class QRedis(QObject):

    keyRenamed = Signal(object, object)
    keysDeleted = Signal()

    TYPE_MAP = {
        type(None): "none",
        str: "string",
        dict: "hash",
        list: "list",
        set: "set",
    }

    GET_TYPE_MAP = {
        "none": lambda r, v: None,
        "string": lambda r, k: r.redis.get(k),
        "hash": lambda r, k: r.redis.hgetall(k),
        "list": lambda r, k: r.redis.lrange(k, 0, -1),
        "set": lambda r, k: r.redis.smembers(k),
    }

    SET_TYPE_MAP = collections.defaultdict(
        lambda: lambda r, k, v: _set(r.redis, k, v),
        {
            type(None): lambda r, k, v: r.delete(k),
            dict: lambda r, k, v: r.redis.hmset(k, v),
            list: lambda r, k, v: _set_list(r.redis, k, v),
            set: lambda r, k, v: _set_set(r.redis, k, v),
        },
    )

    def __init__(self, *args, **kwargs):
        if args:
            parent, args = args[0], args[1:]
        else:
            parent = kwargs.pop("parent", None)
        kwargs.setdefault("decode_responses", True)
        super(QRedis, self).__init__(parent)
        self.redis = Redis(*args, **kwargs)
        # self.__cache = {}

    def __getattr__(self, name):
        return getattr(self.redis, name)

    def get(self, key, default=None):
        if not self.exists(key):
            return default
        dtype, ttl = self.type(key), self.ttl(key)
        ttl = -1 if ttl is None else ttl  # handle redis < 2.8
        value = self.GET_TYPE_MAP[dtype](self, key)
        return KeyItem(self, key, dtype, ttl, value)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self.SET_TYPE_MAP[type(value)](self, key, value)

    def __delitem__(self, key):
        self.delete(key)

    def has_key(self, key):
        return self.exists(key)

    def delete(self, *keys):
        self.redis.delete(*keys)
        self.keysDeleted.emit()

    def rename(self, old_key, new_key):
        old_item = self[old_key]
        self.redis.rename(old_key, new_key)
        new_item = self[new_key]
        self.keyRenamed.emit(old_item, new_item)
