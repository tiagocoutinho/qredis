import os
import re
import sys
import pprint
import logging
import collections

import redis

from .qt import Qt, QMainWindow, QApplication, QTreeWidget, QTreeWidgetItem, \
                QMessageBox, QIcon, QFont, QMenu, QSize, ui_loadable
from .dialog import OpenRedisDialog

_this_dir = os.path.dirname(__file__)
_res_dir = os.path.join(_this_dir, 'images')
_redis_icon = os.path.join(_res_dir, 'redis_logo.png')
_key_icon = os.path.join(_res_dir, 'key.png')


def redis_strs(redis):
    info = redis.connection_pool.connection_kwargs
    if 'path' in info: # unix socket
        addr = info['path']
    elif 'host' in info:
        addr = '{0}:{1}'.format(info['host'], info['port'])
    else:
        addr = '???'
    return 'Redis({0})'.format(addr), 'db={0}'.format(info['db']), '', ''


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


def fill_item(item, data):
    for key, value in data.items():
        child = KeyItem(key, value, item)
        children = value['children']
        fill_item(child, children)


class RedisItem(QTreeWidgetItem):

    SplitRE = re.compile("\:|\.")

    def __init__(self, redis, parent=None):
        super(RedisItem, self).__init__(parent, redis_strs(redis))
        self.setIcon(0, QIcon(_redis_icon))
        self.setToolTip(0, 'Click to update')
        self.redis = redis

    def update(self):
        self.takeChildren()
        root_children = collections.OrderedDict()
        for key in sorted(self.redis.keys()):
            children = root_children
            for sub_key in self.SplitRE.split(key):
                item = children.setdefault(sub_key, dict(type='', children=collections.OrderedDict()))
                children = item['children']
            item['key'] = key
        fill_item(self, root_children)


class KeyItem(QTreeWidgetItem):

    MaxValueSize = 256
    ValueContinue = ' [...]'

    def __init__(self, key, data, parent):
        super(KeyItem, self).__init__(parent, [key] + 3*[''])
        self.setToolTip(0, 'Click to update')
        icon = QIcon(_key_icon) if 'key' in data else QIcon.fromTheme('folder')
        self.setIcon(0, icon)
        self.setFont(3, QFont("Monospace"))
        self.__data = data
        self.root_item = self.__calc_root()

    def __calc_root(self):
        root = self
        while root.parent():
            root = root.parent()
        return root

    @property
    def key(self):
        return self.__data.get('key')

    @property
    def redis(self):
        return self.root_item.redis

    def update(self):
        redis, key = self.redis, self.key
        if self.key is None:
            return
        dtype, ttl = redis.type(key), redis.ttl(key)
        self.setText(1, dtype)
        self.setText(2, str(ttl or ''))
        if dtype == 'none':
            self.parent().removeChild(self)
            return
        value = redis_value(redis, self.key, dtype=dtype)
        text = pprint.pformat(value) if value else '???'
        if len(text) > self.MaxValueSize:
            text = text[:128-len(self.ValueContinue)] + self.ValueContinue
        self.setText(3, text)


@ui_loadable
class RedisTree(QMainWindow):

    Columns = 'Key', 'Type', 'TTL', 'Value'

    DefaultSize = QSize(800, 600)

    def __init__(self, parent=None):
        super(RedisTree, self).__init__(parent)
        self.load_ui()
        ui = self.ui
        tree = self.ui.tree
        header = tree.header()
        header.resizeSection(0, 250)
        tree.itemClicked.connect(self.__on_update_item)
        tree.itemSelectionChanged.connect(self.__on_selection_changed)
        ui.add_key_action.triggered.connect(self.__on_add_key)
        ui.remove_key_action.triggered.connect(self.__on_remove_key)
        ui.touch_key_action.triggered.connect(self.__on_touch_key)

        ui.open_db_action.triggered.connect(self.__on_open_db)
        ui.flush_db_action.triggered.connect(self.__on_flush_db)

    def contextMenuEvent(self, event):
        print 1

    def get_selected_items(self):
        items = self.ui.tree.selectedItems()
        key_items = [item for item in items if isinstance(item, KeyItem)]
        db_items = [item for item in items if isinstance(item, RedisItem)]
        db_keys = collections.defaultdict(list)
        for key_item in key_items:
            db_keys[key_item.redis].append(key_item.key)
        return dict(all_items=items, key_items=key_items, db_items=db_items,
                    db_keys=db_keys)

    def __on_selection_changed(self):
        ui = self.ui
        selected = self.get_selected_items()
        all_items = selected['all_items']
        key_items = selected['key_items']
        db_items = selected['db_items']
        n_items, n_keys, n_dbs = map(len, (all_items, key_items, db_items))
        ui.add_key_action.setEnabled(n_items == 1)
        ui.update_key_action.setEnabled(n_keys > 0)
        ui.remove_key_action.setEnabled(n_keys > 0)
        ui.persist_key_action.setEnabled(n_keys > 0)
        ui.touch_key_action.setEnabled(n_keys > 0)
        ui.copy_key_action.setEnabled(n_keys > 0)
        ui.flush_db_action.setEnabled(not n_keys and n_dbs)

        ui.close_db_action.setEnabled(n_dbs > 0)
        ui.db_info_action.setEnabled(n_dbs == 1)
        ui.db_info_action.setEnabled(n_dbs == 1)

        #self.swap_db_action.setEnabled(not n_keys and n_dbs == 2)

    def __on_open_db(self):
        redis = OpenRedisDialog.create_redis()
        if redis:
            self.add_redis(redis)

    def __on_flush_db(self):
        pass

    def __on_swap_db(self):
        pass

    def __on_touch_key(self):
        selected = self.get_selected_items()
        db_items = selected['db_items']

    def __on_add_key(self):
        item = self.ui.tree.selectedItems()[0]
        redis, key = item.redis, item.key
        print redis, key

    def __on_remove_key(self):
        selected = self.get_selected_items()
        key_items, db_keys = selected['key_items'], selected['db_keys']
        for db, keys in db_keys.items():
            db.delete(*keys)
        for key_item in key_items:
            key_item.parent().removeChild(key_item)

    def __on_update_item(self, item, column=None):
        try:
            item.update()
        except redis.ConnectionError as ce:
            QMessageBox.critical(self, "Connection Error", str(ce))

    def sizeHint(self):
        return self.DefaultSize

    def minimumSizeHint(self):
        return self.DefaultSize

    def add_redis(self, db):
        item = RedisItem(db)
        self.ui.tree.addTopLevelItem(item)
        try:
            item.update()
        except redis.ConnectionError:
            pass
        item.setExpanded(True)


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='QRedis GUI')
    parser.add_argument('--host', help='Server host name')
    parser.add_argument('-p', '--port', help='Server port', type=int)
    parser.add_argument('-s', '--sock', help='unix server socket')
    parser.add_argument('-n', '--db', help='Database number')
    parser.add_argument('--log-level', default='WARNING', help='log level',
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'])
    args = parser.parse_args()

    fmt = '%(asctime)-15s %(levelname)-5s %(name)s: %(message)s'
    level = getattr(logging, args.log_level.upper())
    logging.basicConfig(format=fmt, level=level)

    kwargs = {}
    if args.host is not None:
        kwargs['host'] = args.host
    if args.port is not None:
        kwargs['port'] = args.port
    if args.sock is not None:
        kwargs['unix_socket_path'] = args.sock
    application = QApplication(sys.argv)
    window = RedisTree()
    if kwargs:
        r = redis.Redis(**kwargs)
        window.add_redis(r)
    window.show()
    sys.exit(application.exec_())


if __name__ == '__main__':
    main()
