import pickle
import collections

import msgpack
import msgpack_numpy
from redis import Redis

from .util import KeyItem
from .qt import QObject, Signal


def msgpack_pack(data):
    return msgpack.packb(data, use_bin_type=True, default=msgpack_numpy.encode)


def msgpack_unpack(buff):
    return msgpack.unpackb(buff, raw=False, object_hook=msgpack_numpy.decode)


def decode_utf8(v):
    return v.decode()


def decode_pickle(v):
    return str(pickle.loads(v))


def decode_msgpack(v):
    return str(msgpack_unpack(v))


DECODES = [(decode_utf8, "utf-8"),
           (decode_pickle, "pickle"),
           (decode_msgpack, "msgpack"),
           (str, "raw")]


def decode(value):
    for decoder, dtype in DECODES:
        try:
            return decoder(value)
        except Exception:
            continue


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

    def __init__(self, *args, **kwargs):
        if args:
            parent, args = args[0], args[1:]
        else:
            parent = kwargs.pop("parent", None)
        #kwargs.setdefault("decode_responses", True)
        super(QRedis, self).__init__(parent)

        self._get_type_map = {
            "none": lambda v: None,
            "string": self._get,
            "hash": self._hgetall,
            "list": self._lgetall,
            "set": self._sgetall,
        }

        self._set_type_map = collections.defaultdict(
            lambda: lambda r, k, v: _set(r.redis, k, v),
            {
                type(None): lambda k, v: self.delete(k),
                dict: lambda k, v: self.redis.hmset(k, v),
                list: lambda k, v: _set_list(self.redis, k, v),
                set: lambda k, v: _set_set(self.redis, k, v),
            },
        )

        self.redis = Redis(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.redis, name)

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key, value):
        self._set_type_map[type(value)](self, key, value)

    def __delitem__(self, key):
        self.delete(key)

    def _get(self, key):
        return decode(self.redis.get(key))

    def _hgetall(self, key):
        return {decode(k): decode(v) for k, v in self.redis.hgetall(key).items()}

    def _lgetall(self, key):
        return [decode(i) for i in self.redis.lrange(key, 0, -1)]

    def _sgetall(self, key):
        return {decode(i) for i in self.redis.smembers(key)}

    def get(self, key, default=None):
        if not self.exists(key):
            return default
        dtype, ttl = self.type(key), self.ttl(key)
        ttl = -1 if ttl is None else ttl  # handle redis < 2.8
        value = self._get_type_map[dtype](key)
        return KeyItem(self, key, dtype, ttl, value)

    def type(self, name):
        return self.redis.type(name).decode()

    def keys(self, pattern):
        return [k.decode() for k in self.redis.keys(pattern)]

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
