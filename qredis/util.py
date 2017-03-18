import os
import sys
import collections

KeyItem = collections.namedtuple('KeyItem', 'redis key type ttl value')


def redis_str(redis, filter=None):
    info = redis.connection_pool.connection_kwargs
    if 'path' in info: # unix socket
        addr = info['path']
    elif 'host' in info:
        addr = '{0}:{1}'.format(info['host'], info['port'])
    else:
        addr = '???'
    db = 'db={0}'.format(info['db'])
    if filter:
        name = 'DB {0} @ {1}, filt={2}'.format(info['db'], addr, filter)
    else:
        name = 'DB {0} @ {1}'.format(info['db'], addr)
    return name


def redis_value(redis, key, dtype=None):
    dtype = dtype or redis.type(key)
    value = None
    if dtype == 'string':
        value = redis.get(key)
    elif dtype == 'hash':
        value = redis.hgetall(key)
    elif dtype == 'list':
        value = redis.lrange(key, 0, -1)
    elif dtype == 'set':
        value = redis.smembers(key)
    return value


def redis_key_split(key, chars='.'):
    result, curr = [], ''
    for char in key:
        if char in chars:
            result.append(curr)
            curr = ''
        curr += char
    if curr:
        result.append(curr)
    return result


__startup_cwd = os.getcwd()
def restart():
    if 'linux' in sys.platform.lower():
        with open('/proc/{0}/cmdline'.format(os.getpid())) as f:
            args = [arg for arg in f.read().split('\x00') if arg]
            executable = args[0]
    else:
        args = sys.argv[:]
        executable = sys.executable

    os.chdir(__startup_cwd)
    os.execvp(executable, args)
