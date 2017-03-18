from functools import partial
from collections import namedtuple

from .util import redis_str
from .qt import QWidget, QStackedLayout, QTableWidgetItem, QDialogButtonBox, \
                Signal, ui_loadable

Item = namedtuple('Item', 'redis key type ttl value')

ModifiedStyle = 'background-color: rgb(255,200,200);'


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
class ListEditor(QWidget):

    def __init__(self, parent=None):
        super(ListEditor, self).__init__(parent)
        self.load_ui()

    def set_item(self, item):
        self.item = item
        table = self.ui.table
        table.clearContents()
        table.setRowCount(len(item.value))
        for row, value in enumerate(sorted(item.value)):
            table.setItem(row, 0, QTableWidgetItem(value))


@ui_loadable
class SetEditor(QWidget):

    def __init__(self, parent=None):
        super(SetEditor, self).__init__(parent)
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
        self.ui.key_value.textChanged.connect(self.__on_text_changed)
        self.ui.incr_button.clicked.connect(partial(self.__incr_by, scale=1))
        self.ui.decr_button.clicked.connect(partial(self.__incr_by, scale=-1))
        self.ui.apply_button.clicked.connect(self.__on_apply)
        self.ui.revert_button.clicked.connect(self.__on_revert)

    def set_item(self, item):
        self.original_item = self.item = item
        self.ui.key_value.setPlainText(item.value)

    @property
    def modified(self):
        return self.original_item != self.item

    def __on_revert(self):
        self.set_item(self.original_item)

    def __on_apply(self):
        i = self.item
        try:
            i.redis.set(i.key, i.value)
            self.original_item = i
        except Exception as e:
            print 'error', str(e)
        self.__update()

    def __on_text_changed(self):
        self.item = self.item._replace(value=self.ui.key_value.toPlainText())
        self.__update()

    def __update(self):
        ui = self.ui
        modified = self. modified
        ui.apply_button.setEnabled(modified)
        ui.revert_button.setEnabled(modified)
        style = ModifiedStyle if modified else ''
        ui.key_value.setStyleSheet(style)


    def __incr_by(self, scale=1):
        step = self.ui.step_value.value() * scale
        text = self.ui.key_value.toPlainText()
        value = None
        try:
            value = int(text)
            step = int(step)
        except ValueError:
            try:
                value = float(text)
            except ValueError:
                pass
        if value is not None:
            self.ui.key_value.setPlainText(str(value + step))


@ui_loadable
class RedisItemEditor(QWidget):

    def __init__(self, parent=None):
        super(RedisItemEditor, self).__init__(parent)
        self.load_ui()
        self.__original_item = None
        self.__item = None
        ui = self.ui
        layout = QStackedLayout(ui.type_editor)
        layout.setContentsMargins(3, 3, 3, 3)
        self.none_editor = QWidget()
        self.simple_editor = SimpleEditor()
        self.hash_editor = HashEditor()
        self.seq_editor = ListEditor()
        self.set_editor = SetEditor()
        layout.addWidget(self.none_editor)
        layout.addWidget(self.simple_editor)
        layout.addWidget(self.hash_editor)
        layout.addWidget(self.seq_editor)
        layout.addWidget(self.set_editor)
        self.type_editor_map = {
            'none': self.none_editor,
            'string': self.simple_editor,
            'hash': self.hash_editor,
            'list': self.seq_editor,
            'set': self.set_editor,
        }
        ui.key_name.textChanged.connect(self.__on_key_name_changed)
        ui.key_name.editingFinished.connect(self.__on_key_name_applyed)
        ui.ttl_value.valueChanged.connect(self.__on_ttl_changed)
        ui.apply_ttl_button.clicked.connect(self.__on_apply_ttl)
        ui.refresh_button.clicked.connect(self.__on_refresh)
        ui.persist_button.clicked.connect(self.__on_persist)
        ui.delete_button.clicked.connect(self.__on_delete)

    def __on_apply_ttl(self):
        if self.ttl_modified:
            item, original_item = self.__item, self.__original_item
            try:
                item.redis.expire(item.key, item.ttl)
                self.__original_item = original_item._replace(ttl=item.ttl)
            except Exception as e:
                print 'error', str(e)
            self.__update()

    def __on_key_name_changed(self, key):
        self.__item = self.__item._replace(key=key)
        self.__update()

    def __on_key_name_applyed(self):
        if self.name_modified:
            item, original_item = self.__item, self.__original_item
            try:
                item.redis.rename(original_item.key, item.key)
                self.__original_item = original_item._replace(key=item.key)
            except Exception as e:
                print 'error', str(e)
            self.__update()

    def __on_ttl_changed(self, ttl):
        self.__item = self.__item._replace(ttl=ttl)
        self.__update()

    def __on_refresh(self):
        self.set_item(self.__item.redis, self.__item.key)

    def __on_persist(self):
        try:
            self.__item.redis.persist(self.__item.key)
        except Exception as e:
            print 'error', str(e)

    def __on_delete(self):
        try:
            self.__item.redis.delete(self.__item.key)
        except Exception as e:
            print 'error', str(e)

    @property
    def name_modified(self):
        return self.__item.key != self.__original_item.key

    @property
    def ttl_modified(self):
        return self.__item.ttl != self.__original_item.ttl

    def __update(self):
        ui = self.ui
        name_modified, ttl_modified = self.name_modified, self.ttl_modified
        ui.key_name.setStyleSheet(ModifiedStyle if name_modified else '')
        ui.ttl_value.setStyleSheet(ModifiedStyle if ttl_modified else '')
        ui.apply_ttl_button.setEnabled(ttl_modified)

    def set_item(self, redis, key):
        item = redis.get(key)
        if item is None:
            editor = self.none_editor
            ttl = -1
        else:
            editor = self.type_editor_map[item.type]
            editor.set_item(item)
            ttl = item.ttl
        self.__original_item = self.__item = item
        self.ui.type_editor.layout().setCurrentWidget(editor)
        self.ui.key_name.setText(key)
        self.ui.ttl_value.setValue(ttl)


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
