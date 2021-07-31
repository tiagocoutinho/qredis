import os
import logging
import functools

from .qt import (
    Qt,
    QMainWindow,
    QApplication,
    QModelIndex,
    QAbstractItemModel,
    QSortFilterProxyModel,
    QToolButton,
    QMessageBox,
    QInputDialog,
    QIcon,
    QMenu,
    Signal,
    ui_loadable,
)
from .util import KeyItem as Item, redis_str
from .redis import QRedis


_this_dir = os.path.dirname(__file__)
_res_dir = os.path.join(_this_dir, "images")
_redis_icon = os.path.join(_res_dir, "redis_logo.png")
_key_icon = os.path.join(_res_dir, "key.png")
_folder_icon = os.path.join(_res_dir, "folder.png")

NodeRole = Qt.UserRole
KeyNameRole = Qt.UserRole + 1


class Node:
    __slots__ = ["name", "full_name", "key", "parent", "children", "items"]

    def __init__(self, name, full_name, key=None, parent=None, children=None):
        self.name = name
        self.full_name = full_name
        self.key = key
        self.parent = parent
        self.children = children or {}
        self.items = list(self.children)

    def __setitem__(self, name, node):
        self.children[name] = node
        self.items.append(name)

    def __getitem__(self, name_or_index):
        if isinstance(name_or_index, int):
            name = self.items[name_or_index]
        else:
            name = name_or_index
        return self.children[name]

    def __len__(self):
        return len(self.children)

    def __repr__(self):
        if self.is_key():
            return f"KeyNode(key={self.key}, children={self.items})"
        else:
            return f"Node(name={self.name}, children={self.items})"

    def is_db(self):
        return False

    def is_key(self):
        return self.key is not None

    def key_item(self, redis):
        if self.is_key():
            return redis.get(self.key)


class RedisNode(Node):

    def is_db(self):
        return True

    def __repr__(self):
        return f"Redis(name={self.name})"


def tree(redis, keys, sep):
    name, long_name = redis_str(redis)
    root = Node(None, None)
    rnode = RedisNode(name, long_name, parent=root)
    rnode.redis = redis
    root[name] = rnode
    for key in keys:
        parts = key.split(sep)
        parent = rnode
        partial = []
        for part in parts:
            partial.append(part)
            try:
                node = parent[part]
            except KeyError:
                full_name = sep.join(partial)
                node = Node(part, full_name, parent=parent)
                parent[part] = node
            parent = node
        node.key = key
    return root


class RedisKeyModel(QAbstractItemModel):

    def __init__(self, qredis, filter="*", sep=":"):
        super().__init__()
        self.qredis = qredis
        self.filter = filter
        self.separator = sep
        self._key_icon = QIcon(_key_icon)
        self._redis_icon = QIcon(_redis_icon)
        self._folder_icon = QIcon(_folder_icon)
        self._refresh()

    def _refresh(self):
        keys = sorted(self.qredis.keys(self.filter))
        self.tree = tree(self.qredis, keys, self.separator)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            parent_node = parent.internalPointer()
            return len(parent_node)
        else:
            return len(self.tree)

    def data(self, index, role=Qt.DisplayRole):
        if role in {Qt.DisplayRole, Qt.AccessibleTextRole}:
            return index.internalPointer().name
        elif role == Qt.DecorationRole:
            node = index.internalPointer()
            if node.is_key():
                return self._key_icon
            elif node.is_db():
                return self._redis_icon
            else:
                return self._folder_icon
        elif role == Qt.ToolTipRole:
            node = index.internalPointer()
            if node.is_key():
                key_item = node.key_item(self.qredis)
                return "?" if key_item is None else key_item.toolTip()
            else:
                return node.full_name
        elif role == NodeRole:
            return index.internalPointer()
        elif role == KeyNameRole:
            node = index.internalPointer()
            return node.full_name
        elif role == Qt.EditRole:
            node = index.internalPointer()
            if node.is_key():
                return node.key

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid():
            parent_node = parent.internalPointer()
            node = parent_node[row - 1]
        else:
            node = self.tree[row]
        return self.createIndex(row, column, node)

    def parent(self, index):
        node = index.internalPointer()
        if node is None:
            return QModelIndex()
        parent = node.parent
        grandparent = parent.parent
        if grandparent is None:
            return QModelIndex()
        row = grandparent.items.index(parent.name)
        return self.createIndex(row, 0, parent)

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        node = index.internalPointer()
        value = Qt.ItemIsEnabled
        if node.is_key():
            value |= Qt.ItemIsSelectable
            value |= Qt.ItemIsEditable | Qt.ItemIsDragEnabled
        return value

    def refresh(self):
        self.beginResetModel()
        try:
            self._refresh()
        finally:
            self.endResetModel()


@ui_loadable
class RedisTree(QMainWindow):

    addKey = Signal(object)
    currentChanged = Signal(object)

    def __init__(self, redis, parent=None):
        super(RedisTree, self).__init__(parent)
        self.load_ui()
        ui = self.ui
        self.redis = redis
        self.source_model = RedisKeyModel(redis)
        self.sort_filter_model = QSortFilterProxyModel()
        self.sort_filter_model.setFilterRole(KeyNameRole)
        self.sort_filter_model.setSourceModel(self.source_model)
        ui.tree.setModel(self.sort_filter_model)
        selection = ui.tree.selectionModel()
        selection.currentChanged.connect(self._on_current_changed)
        selection.selectionChanged.connect(self._on_selection_changed)
        # TODO: fix bug search of type "bl04:" still gives no result
        ui.filter_container.setVisible(False)
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
        ui.add_string_action.triggered.connect(
            functools.partial(self._on_add_key, "string")
        )
        ui.add_list_action.triggered.connect(
            functools.partial(self._on_add_key, "list")
        )
        ui.add_set_action.triggered.connect(functools.partial(self._on_add_key, "set"))
        ui.add_hash_action.triggered.connect(
            functools.partial(self._on_add_key, "hash")
        )

        ui.update_db_action.triggered.connect(self._on_update_db)
        ui.flush_db_action.triggered.connect(self._on_flush_db)
        ui.remove_key_action.triggered.connect(self._on_remove_key)
        ui.touch_key_action.triggered.connect(self._on_touch_key)
        ui.persist_key_action.triggered.connect(self._on_persist_key)
        ui.copy_key_action.triggered.connect(self._on_copy_key)
        ui.filter_edit.textChanged.connect(self._on_filter_changed)

    def contextMenuEvent(self, event):
        pass

    def _get_selected_keys(self):
        selection = self.ui.tree.selectionModel()
        indexes = (self.sort_filter_model.mapToSource(i) for i in selection.selectedIndexes())
        nodes = (self.source_model.data(i, NodeRole) for i in indexes)
        keys = tuple(node.key for node in nodes if node is not None and node.is_key())
        return keys

    def _on_filter_changed(self, text):
        if not text.endswith("*"):
            text += "*"
        self.sort_filter_model.setFilterWildcard(text)

    def _on_current_changed(self, current, previous):
        current = self.sort_filter_model.mapToSource(current)
        node = self.source_model.data(current, Qt.UserRole)
        self.currentChanged.emit(node)

    def _on_selection_changed(self, selected, deselected):
        indexes = (self.sort_filter_model.mapToSource(i) for i in selected.indexes())
        nodes = (self.source_model.data(i, NodeRole) for i in indexes)
        nodes = [node for node in nodes if node is not None]
        nodes_selected = bool(nodes)
        ui = self.ui
        ui.remove_key_action.setEnabled(nodes_selected)
        ui.touch_key_action.setEnabled(nodes_selected)
        ui.persist_key_action.setEnabled(nodes_selected)
        ui.copy_key_action.setEnabled(len(nodes) == 1)

    def _on_flush_db(self):
        result = QMessageBox.question(
            self, "Danger!",
            "This action will delete all data from the current database.\n" \
            "Are you absolutely sure?")
        if result == QMessageBox.Yes:
            self.redis.flushdb()
            self.source_model.refresh()

    def _on_update_db(self):
        self.source_model.refresh()

    def _on_touch_key(self):
        keys = self._get_selected_keys()
        if keys:
            self.redis.touch(*keys)

    def _on_persist_key(self):
        keys = self._get_selected_keys()
        for key in keys:
            self.redis.persist(key)

    def _on_add_key(self, dtype):
        value = None
        if dtype == "string":
            value = ""
        elif dtype == "list":
            value = []
        elif dtype == "set":
            value = set()
        elif dtype == "hash":
            value = {}
        item = Item(self.redis, "", dtype, -1, value)
        self.addKey.emit(item)

    def _on_remove_key(self):
        keys = self._get_selected_keys()
        if keys:
            self.redis.delete(*keys)
        self.ui.tree.clearSelection()

    def _on_copy_key(self):
        keys = self._get_selected_keys()
        assert len(keys) == 1
        src = keys[0]
        dst, ok = QInputDialog.getText(self, f"Copy {src!r} to...", "New key")
        if ok:
            # redis.copy() only >= 6.2
            #self.redis.copy(src, dst)
            self.redis[dst] = self.redis[src].value
            self.source_model.refresh()


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
