import os
import re
import collections

import redis

from .ui import ui_loadable
from .qt import Qt, QMainWindow, QApplication, QDialog, QMdiSubWindow, QLabel, QTreeWidgetItem, QIcon


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

#key, value, type, TTL

def fill_item(item, data, max_expand_level=1, level=0):
    for key, value in data.items():
        children = value['children']
        child = QTreeWidgetItem(item, [key] + 3*[''])
        if 'key' in value:
            icon = QIcon(_key_icon)
        else:
            icon = QIcon.fromTheme('folder')
        child.setIcon(0, icon)
        child.setToolTip(0, value.get('tooltip', ''))
        child.setData(0, Qt.UserRole, value)
        fill_item(child, children, level=level+1)

    if level < max_expand_level:
        item.setExpanded(True)


class RedisItem(QTreeWidgetItem):

    SplitRE = re.compile("\:|\.")

    def __init__(self, redis, parent=None):
        super(RedisItem, self).__init__(parent, redis_strs(redis))
        self.setIcon(0, QIcon(_redis_icon))
        self.redis = redis
        self.update()

    def update(self):
        self.takeChildren()
        root_children = {}
        for key in self.redis.keys():
            children = root_children
            for sub_key in self.SplitRE.split(key):
                item = children.setdefault(sub_key, dict(type='', children={}))
                children = item['children']
            item['key'] = key
            item['tooltip'] = key
        fill_item(self, root_children)


@ui_loadable
class RedisWindow(QMainWindow):

    def __init__(self, parent=None):
        super(RedisWindow, self).__init__(parent)
        self.load_ui()
        self.setWindowIcon(QIcon(_redis_icon))
        ui = self.ui
        ui.about_dialog = AboutDialog()
        ui.quit_action.triggered.connect(QApplication.quit)
        ui.about_action.triggered.connect(lambda: ui.about_dialog.exec_())
        ui.db_tree.currentItemChanged.connect(self.__on_item_changed)
        ui.db_tree.itemDoubleClicked.connect(self.__on_item_double_clicked)

    def __on_item_changed(self, current, previous):
        pass

    def __on_item_double_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if data is None:
            return
        key = data.get('key')
        if key is None:
            return
        root = item
        while root.parent():
            root = root.parent()
        redis = root.redis
        dtype = redis.type(key)
        item.setText(2, dtype)
        value = None
        if dtype == 'string':
            value = redis.get(key)
        elif dtype == 'hash':
            item.takeChildren()
            for k, v in redis.hgetall(key).items():
                QTreeWidgetItem(item, [k, v, 'string', ''])
        elif dtype == 'list':
            value = redis.lrange(key, 0, -1)
        if value is not None:
            item.setText(1, str(value))

    #def update_value()

    def add(self, redis):
        RedisItem(redis, self.ui.db_tree)


class AboutDialog(QDialog):
    """Create the necessary elements to show helpful text in a dialog."""

    def __init__(self, parent=None):
        """Display a dialog that shows application information."""
        super(AboutDialog, self).__init__(parent)
        self.setWindowTitle('About')


def main():
    import sys
    from bliss.config.conductor.client import get_cache
    application = QApplication(sys.argv)
    window = RedisWindow()
    window.add(get_cache())
    window.show()
    sys.exit(application.exec_())
