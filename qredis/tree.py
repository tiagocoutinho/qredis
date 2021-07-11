import os
import logging
import functools
import collections

from .qt import (
    QMainWindow,
    QApplication,
    QTreeWidgetItem,
    QToolButton,
    QMessageBox,
    QIcon,
    QFont,
    QMenu,
    Signal,
    ui_loadable,
)
from .dialog import OpenRedisDialog
from .util import redis_str, redis_key_split
from .util import KeyItem as Item
from .redis import QRedis, ConnectionError


_this_dir = os.path.dirname(__file__)
_res_dir = os.path.join(_this_dir, "images")
_redis_icon = os.path.join(_res_dir, "redis_logo.png")
_key_icon = os.path.join(_res_dir, "key.png")


def fill_item(item, data):
    result = {}
    for key, value in data.items():
        child = KeyItem(key, value, item)
        children = value["children"]
        result[value["key"]] = child
        result.update(fill_item(child, children))
    return result


class RedisItem(QTreeWidgetItem):

    SplitChars = ".:"

    def __init__(self, redis, filter=None, split_by=SplitChars, parent=None):
        name, _ = redis_str(redis)
        super(RedisItem, self).__init__(parent, [name])
        self.__filter = filter
        self.__split = split_by
        self.key_items = {}
        self.setIcon(0, QIcon(_redis_icon))
        self.redis = redis
        redis.keyRenamed.connect(self.__on_key_renamed)
        redis.keysDeleted.connect(self.__on_keys_deleted)

    def toolTip(self, column):
        return redis_str(self.redis)[1]

    @property
    def filter(self):
        return self.__filter

    @filter.setter
    def filter(self, filter):
        self.__filter = filter
        self.update()

    def update(self):
        self.takeChildren()
        root_children = collections.OrderedDict()
        filt = self.filter or "*"
        for key in sorted(self.redis.keys(filt)):
            children = root_children
            sub_key, sub_keys = "", redis_key_split(key, self.__split)
            for i, name in enumerate(sub_keys):
                sub_key += name
                key_name = name[1:] if i else name
                item = children.setdefault(
                    key_name, dict(type="", children=collections.OrderedDict())
                )
                children = item["children"]
                item["name"] = key_name
                item["key"] = sub_key
                item["has_value"] = False
                item["has_value"] = True
        self.key_items = fill_item(self, root_children)

    def __on_key_renamed(self, old_item, new_item):
        old_key, new_key = old_item.key, new_item.key
        if not old_key:
            return
        old_sub_keys = redis_key_split(old_key, self.__split)
        new_sub_keys = redis_key_split(new_key, self.__split)
        parent_changed = old_sub_keys[:-1] != new_sub_keys[:-1]
        item = self.key_items.pop(old_key)
        if parent_changed:
            self.update()
        else:
            label = new_sub_keys[-1][1:] if len(new_sub_keys) > 1 else new_sub_keys[-1]
            self.key_items[new_key] = item
            item.rename(new_key, label)

    def __on_keys_deleted(self):
        self.update()

    @property
    def redis_item(self):
        return self


class KeyItem(QTreeWidgetItem):
    def __init__(self, key, data, parent):
        super(KeyItem, self).__init__(parent, [key])
        icon = QIcon(_key_icon) if data["has_value"] else QIcon.fromTheme("folder")
        self.setIcon(0, icon)
        self.setFont(3, QFont("Monospace"))
        self.__data = data
        self.root_item = self.__calc_root()

    def __calc_root(self):
        root = self
        while root.parent():
            root = root.parent()
        return root

    def rename(self, key, label):
        self.__data["key"] = key
        self.setText(0, label)

    @property
    def key(self):
        return self.__data.get("key")

    @property
    def has_value(self):
        return self.__data.get("has_value", False)

    @property
    def redis(self):
        return self.root_item.redis

    @property
    def redis_item(self):
        return self.root_item


@ui_loadable
class RedisTree(QMainWindow):

    addKey = Signal(object)
    selectionChanged = Signal(object)

    def __init__(self, parent=None):
        super(RedisTree, self).__init__(parent)
        self.load_ui()
        self.__selected_items = dict(
            all_items=[], key_items=[], db_items=[], db_keys={}
        )
        ui = self.ui
        header = ui.tree.header()
        header.resizeSection(0, 220)
        ui.open_db_action.setIcon(QIcon(_redis_icon))
        add_menu = QMenu("Add")
        ui.add_string_action = add_menu.addAction("string")
        ui.add_list_action = add_menu.addAction("list")
        ui.add_set_action = add_menu.addAction("set")
        ui.add_hash_action = add_menu.addAction("hash")
        add_button = QToolButton()
        add_button.setMenu(add_menu)
        add_button.setPopupMode(QToolButton.InstantPopup)
        add_button.setIcon(QIcon.fromTheme("list-add"))
        ui.add_key_action = ui.db_toolbar.insertWidget(ui.remove_key_action, add_button)
        ui.add_key_action.setEnabled(False)

        ui.tree.itemSelectionChanged.connect(self.__on_item_selection_changed)
        self.selectionChanged.connect(self.__on_selection_changed)
        ui.add_string_action.triggered.connect(
            functools.partial(self.__on_add_key, "string")
        )
        ui.add_list_action.triggered.connect(
            functools.partial(self.__on_add_key, "list")
        )
        ui.add_set_action.triggered.connect(functools.partial(self.__on_add_key, "set"))
        ui.add_hash_action.triggered.connect(
            functools.partial(self.__on_add_key, "hash")
        )

        ui.remove_key_action.triggered.connect(self.__on_remove_key)
        ui.touch_key_action.triggered.connect(self.__on_touch_key)

        ui.open_db_action.triggered.connect(self.__on_open_db)
        ui.close_db_action.triggered.connect(self.__on_close_db)
        ui.update_db_action.triggered.connect(self.__on_update_db)
        ui.flush_db_action.triggered.connect(self.__on_flush_db)

    def contextMenuEvent(self, event):
        pass

    @property
    def selected_items(self):
        return self.__selected_items

    def __update_selected_items(self):
        items = self.ui.tree.selectedItems()
        key_items = [item for item in items if isinstance(item, KeyItem)]
        db_items = [item for item in items if isinstance(item, RedisItem)]
        db_keys = collections.defaultdict(list)
        for key_item in key_items:
            db_keys[key_item.redis].append(key_item.key)
        si = self.__selected_items
        si["all_items"] = items
        si["key_items"] = key_items
        si["db_items"] = db_items
        si["db_keys"] = db_keys
        return si

    def __on_item_selection_changed(self):
        selected = self.__update_selected_items()
        self.selectionChanged.emit(selected)

    def __on_selection_changed(self, selected):
        ui = self.ui
        all_items = selected["all_items"]
        key_items = selected["key_items"]
        db_items = selected["db_items"]
        n_items, n_keys, n_dbs = map(len, (all_items, key_items, db_items))
        ui.add_key_action.setEnabled(n_items == 1)
        ui.remove_key_action.setEnabled(n_keys > 0)
        ui.persist_key_action.setEnabled(n_keys > 0)
        ui.touch_key_action.setEnabled(n_keys > 0)
        ui.copy_key_action.setEnabled(n_keys > 0)
        ui.flush_db_action.setEnabled(not n_keys and n_dbs)
        ui.update_db_action.setEnabled(n_items > 0)
        ui.close_db_action.setEnabled(n_dbs > 0)

    def __on_open_db(self):
        try:
            redis = OpenRedisDialog.create_redis()
            if redis:
                self.add_redis(redis)
        except Exception as error:
            QMessageBox.warning(self, "Connection error!", repr(error))

    def __on_close_db(self):
        pass

    def __on_flush_db(self):
        pass

    def __on_update_db(self):
        db_items = []
        for item in self.selected_items["all_items"]:
            db_items.append(item.redis_item)
        for db_item in db_items:
            db_item.update()

    def __on_swap_db(self):
        pass

    def __on_touch_key(self):
        selected = self.selected_items
        db_items = selected["db_items"]

    def __on_add_key(self, dtype):
        tree_item = self.ui.tree.selectedItems()[0]
        value = None
        if dtype == "string":
            value = ""
        elif dtype == "list":
            value = []
        elif dtype == "set":
            value = set()
        elif dtype == "hash":
            value = {}
        item = Item(tree_item.redis, "", dtype, -1, value)
        self.addKey.emit(item)

    def __on_remove_key(self):
        selected = self.selected_items
        key_items, db_keys = selected["key_items"], selected["db_keys"]
        for db, keys in db_keys.items():
            db.delete(*keys)
        self.ui.tree.clearSelection()

    def __on_update_item(self, item, column=None):
        try:
            item.update()
        except ConnectionError as ce:
            QMessageBox.critical(self, "Connection Error", str(ce))

    def add_redis(self, db):
        item = RedisItem(db)
        self.ui.tree.addTopLevelItem(item)
        try:
            item.update()
        except ConnectionError:
            pass
        item.setExpanded(True)


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="QRedis GUI")
    parser.add_argument("--host", help="Server host name")
    parser.add_argument("-p", "--port", help="Server port", type=int)
    parser.add_argument("-s", "--sock", help="unix server socket")
    parser.add_argument("-n", "--db", help="Database number")
    parser.add_argument(
        "--log-level",
        default="WARNING",
        help="log level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
    )
    args = parser.parse_args()

    fmt = "%(asctime)-15s %(levelname)-5s %(name)s: %(message)s"
    level = getattr(logging, args.log_level.upper())
    logging.basicConfig(format=fmt, level=level)

    kwargs = {}
    if args.host is not None:
        kwargs["host"] = args.host
    if args.port is not None:
        kwargs["port"] = args.port
    if args.sock is not None:
        kwargs["unix_socket_path"] = args.sock
    application = QApplication(sys.argv)
    window = RedisTree()
    if kwargs:
        r = QRedis(**kwargs)
        window.add_redis(r)
    window.show()
    sys.exit(application.exec_())


if __name__ == "__main__":
    main()
