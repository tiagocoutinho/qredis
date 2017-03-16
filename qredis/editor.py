from functools import partial
from collections import namedtuple

from redis import Redis

from .qt import QWidget, QStackedLayout, QTableWidgetItem, QDialogButtonBox, ui_loadable
from .util import redis_str

Item = namedtuple('Item', 'redis key type ttl value')


@ui_loadable
class HashEditor(QWidget):

    def __init__(self, parent=None):
        super(HashEditor, self).__init__(parent)
        self.load_ui()

    def set_item(self, item):
        self.item = item
        table = self.ui.table
        table.clearContents()
        table.setRowCount(len(item.value))
        for row, key in enumerate(sorted(item.value)):
            table.setItem(row, 0, QTableWidgetItem(key))
            table.setItem(row, 1, QTableWidgetItem(item.value[key]))


@ui_loadable
class SeqEditor(QWidget):

    def __init__(self, parent=None):
        super(SeqEditor, self).__init__(parent)
        self.load_ui()

    def set_item(self, item):
        self.item = item
        table = self.ui.table
        table.clearContents()
        table.setRowCount(len(item.value))
        for row, value in enumerate(sorted(item.value)):
            table.setItem(row, 0, QTableWidgetItem(value))


@ui_loadable
class SimpleEditor(QWidget):

    def __init__(self, parent=None):
        super(SimpleEditor, self).__init__(parent)
        self.load_ui()
        self.ui.key_value.textChanged.connect(self.__on_value_changed)
        self.ui.incr_button.clicked.connect(partial(self.__incr_by, scale=1))
        self.ui.decr_button.clicked.connect(partial(self.__incr_by, scale=-1))
        self.ui.button_box.clicked.connect(self.__on_do)

    def set_item(self, item):
        self.item = item
        self.ui.key_value.setText(item.value)

    def __on_do(self, button):
        role = self.ui.button_box.buttonRole(button)
        if role == QDialogButtonBox.ApplyRole:
            value = self.ui.key_value.text()
            i = self.item
            i.redis.set(i.key, value)
            self.item = Item(i.redis, i.key, i.type, i.ttl, value)
            self.__on_value_changed(value)
        elif role == QDialogButtonBox.ResetRole:
            self.ui.key_value.setText(self.item.value)

    def __on_value_changed(self, text):
        apply_enabled = text != self.item.value
        self.ui.button_box.button(QDialogButtonBox.Apply).setEnabled(apply_enabled)
        self.ui.button_box.button(QDialogButtonBox.Reset).setEnabled(apply_enabled)

    def __incr_by(self, scale=1):
        step = self.ui.step_value.value() * scale
        text = self.ui.key_value.text()
        is_int = False
        is_float = True
        try:
            ivalue = int(text)
            step = int(step)
            self.ui.key_value.setText(str(ivalue + step))
        except ValueError:
            try:
                fvalue = float(text)
                self.ui.key_value.setText(str(fvalue + step))
            except ValueError:
                pass


@ui_loadable
class RedisItemEditor(QWidget):

    def __init__(self, parent=None):
        super(RedisItemEditor, self).__init__(parent)
        self.load_ui()
        self.__item = None
        ui = self.ui
        layout = QStackedLayout(ui.type_editor)
        layout.setContentsMargins(3, 3, 3, 3)
        self.simple_editor = SimpleEditor()
        self.hash_editor = HashEditor()
        self.seq_editor = SeqEditor()
        layout.addWidget(self.simple_editor)
        layout.addWidget(self.hash_editor)
        layout.addWidget(self.seq_editor)
        self.type_editor_map = {
            'string': (self.simple_editor, Redis.get),
            'hash': (self.hash_editor, Redis.hgetall),
            'list': (self.seq_editor, lambda db, key: db.lrange(key, 0, -1)),
            'set': (self.seq_editor, Redis.smembers),
         }

    def set_item(self, redis, key):
        dtype, ttl = redis.type(key), redis.ttl(key)
        self.ui.key_value.setText(key)
        self.ui.ttl_value.setValue(-1 if ttl is None else ttl)
        editor, getter = self.type_editor_map[dtype]
        item = Item(redis, key, ttl, dtype, getter(redis, key))
        self.__item = item
        editor.set_item(item)
        self.ui.type_editor.layout().setCurrentWidget(editor)


@ui_loadable
class RedisDbEditor(QWidget):

    def __init__(self, parent=None):
        super(RedisDbEditor, self).__init__(parent)
        self.load_ui()

    def set_db(self, redis):
        self.ui.name_label.setText(redis_str(redis))
        table = self.ui.info_table
        table.clearContents()
        info = redis.info()
        table.setRowCount(len(info))
        for row, key in enumerate(sorted(info)):
            table.setItem(row, 0, QTableWidgetItem(key))
            table.setItem(row, 1, QTableWidgetItem(str(info[key])))


class RedisEditor(QWidget):

    def __init__(self, parent=None):
        super(RedisEditor, self).__init__(parent)
        self.empty = QWidget(self)
        self.item = RedisItemEditor(self)
        self.db = RedisDbEditor(self)
        layout = QStackedLayout(self)
        layout.addWidget(self.empty)
        layout.addWidget(self.item)
        layout.addWidget(self.db)

    def set_empty(self):
        self.layout().setCurrentWidget(self.empty)

    def set_item(self, redis, key):
        self.layout().setCurrentWidget(self.item)
        self.item.set_item(redis, key)

    def set_db(self, redis):
        self.layout().setCurrentWidget(self.db)
        self.db.set_db(redis)
