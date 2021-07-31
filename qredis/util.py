import os
import sys
import collections


REDIS_TEXT = """\
Db: {db}
Address: {addr}
Client ID: {id}
Client Name: {name}"""


def toolTip(item):
    return f"""\
name: {item.key}
type: {item.type}
TTL: {item.ttl}"""


KeyItem = collections.namedtuple("KeyItem", "redis key type ttl value")
KeyItem.toolTip = toolTip


def redis_str(redis):
    info = redis.connection_pool.connection_kwargs
    db = info["db"]
    cid = redis.client_id()
    cname = redis.client_getname()
    if "path" in info:  # unix socket
        addr = info["path"]
    elif "host" in info:
        addr = "{}:{}".format(info["host"], info["port"])
    else:
        addr = "???"
    ctext = "{} - {}".format(cid, cname) if cname else str(cid)
    text = "DB {} @ {} ({})".format(db, addr, ctext)
    long_text = REDIS_TEXT.format(db=db, addr=addr, id=cid, name=cname or "---")
    return text, long_text


def redis_value(redis, key, dtype=None):
    dtype = dtype or redis.type(key)
    value = None
    if dtype == "string":
        value = redis.get(key)
    elif dtype == "hash":
        value = redis.hgetall(key)
    elif dtype == "list":
        value = redis.lrange(key, 0, -1)
    elif dtype == "set":
        value = redis.smembers(key)
    return value


def redis_key_split(key, chars="."):
    result, curr = [], ""
    for char in key:
        if char in chars:
            result.append(curr)
            curr = ""
        curr += char
    if curr:
        result.append(curr)
    return result


__startup_cwd = os.getcwd()


def restart():
    if "linux" in sys.platform.lower():
        with open("/proc/{0}/cmdline".format(os.getpid())) as f:
            args = [arg for arg in f.read().split("\x00") if arg]
            executable = args[0]
    else:
        args = sys.argv[:]
        executable = sys.executable

    os.chdir(__startup_cwd)
    os.execvp(executable, args)
