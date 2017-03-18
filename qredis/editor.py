from datetime import timedelta
from functools import partial
from collections import namedtuple

from .util import redis_str
from .qt import QWidget, QStackedLayout, QTableWidgetItem, QDialogButtonBox, \
                QIntValidator, Signal, ui_loadable

Item = namedtuple('Item', 'redis key type ttl value')

ModifiedStyle = 'background-color: rgb(255,200,200);'

@ui_loadable
class MultiEditor(QWidget):

    def __init__(self, parent=None):
        super(MultiEditor, self).__init__(parent)
        self.load_ui()
        self.modified = False
        self.ui.table.itemSelectionChanged.connect(self.update_ui)
        self.ui.table.itemChanged.connect(self.item_changed)
        self.ui.add_button.clicked.connect(self.add_item)
        self.ui.delete_button.clicked.connect(self.delete_selection)
        self.ui.revert_button.clicked.connect(self.revert_changes)
        self.ui.apply_button.clicked.connect(self.apply_changes)

    def item_changed(self, item):
        self.modified = True
        self.update_ui()

    def revert_changes(self):
        self.set_item(self.__item)

    def apply_changes(self):
        table, item = self.ui.table, self.__item
        if item.type == 'hash':
            value = {}
            for row in range(table.rowCount()):
                value[table.item(row, 0).text()] = table.item(row, 1).text()
        else:
            value = [table.item(row, 0).text() for row in range(table.rowCount())]
            value = value if item.type == 'list' else set(value)
        item.redis[item.key] = value
        self.__item = item._replace(value=value)
        self.modified = False
        self.update_ui()

    def set_item(self, item):
        self.__item = item
        table = self.ui.table
        table.clearContents()
        dtype, value = item.type, item.value
        table.setRowCount(len(value))
        header = ('Key', 'Value') if dtype == 'hash' else ('Value',)
        table.setColumnCount(len(header))
        table.setHorizontalHeaderLabels(header)
        keys = value if dtype == 'list' else sorted(value)
        for row, key in enumerate(keys):
            table.setItem(row, 0, QTableWidgetItem(key))
        if item.type == 'hash':
            for row, key in enumerate(keys):
                table.setItem(row, 1, QTableWidgetItem(value[key]))
        self.modified = False
        self.update_ui()

    def add_item(self):
        table = self.ui.table
        items = table.selectedIndexes()
        if items:
            row = max([item.row() for item in items])
        else:
            row = table.rowCount()
        table.insertRow(row)
        key_item = QTableWidgetItem()
        table.setItem(row, 0, key_item)
        table.editItem(key_item)
        self.modified = True
        self.update_ui()

    def delete_selection(self):
        table = self.ui.table
        rows = set([item.row() for item in table.selectedIndexes()])
        for row in sorted(rows, reverse=True):
            table.removeRow(row)
        self.modified = True
        self.update_ui()

    def update_ui(self):
        ui, modified = self.ui, self.modified
        style = ModifiedStyle if modified else ''
        selected_count = len(ui.table.selectedIndexes())
        ui.table.setStyleSheet(style)
        ui.apply_button.setEnabled(modified)
        ui.revert_button.setEnabled(modified)
        ui.delete_button.setEnabled(selected_count > 0)


@ui_loadable
class SimpleEditor(QWidget):

    def __init__(self, parent=None):
        super(SimpleEditor, self).__init__(parent)
        self.load_ui()
        ui = self.ui
        ui.key_value.textChanged.connect(self.__on_text_changed)
        ui.incr_button.clicked.connect(partial(self.__incr_by, scale=1))
        ui.decr_button.clicked.connect(partial(self.__incr_by, scale=-1))
        ui.apply_button.clicked.connect(self.__on_apply)
        ui.revert_button.clicked.connect(self.__on_revert)

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
        self.hash_editor = MultiEditor()
        self.seq_editor = MultiEditor()
        self.seq_editor.ui.table.horizontalHeader().setVisible(False)
        self.set_editor = MultiEditor()
        self.set_editor.ui.table.horizontalHeader().setVisible(False)
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
        ui.key_name.editingFinished.connect(self.__on_key_name_applied)
        ttl_validator = QIntValidator()
        ttl_validator.setBottom(-1)
        ui.ttl_value.setValidator(ttl_validator)
        ui.ttl_value.textChanged.connect(self.__on_ttl_changed)
        ui.ttl_value.editingFinished.connect(self.__on_ttl_applied)
        ui.refresh_button.clicked.connect(self.__on_refresh)
        ui.persist_button.clicked.connect(self.__on_persist)
        ui.delete_button.clicked.connect(self.__on_delete)


    def __on_key_name_changed(self, key):
        self.__item = self.__item._replace(key=key)
        self.__update()

    def __on_key_name_applied(self):
        if self.name_modified:
            item, original_item = self.__item, self.__original_item
            try:
                item.redis.rename(original_item.key, item.key)
                self.__original_item = original_item._replace(key=item.key)
            except Exception as e:
                print 'error', str(e)
            self.__update()

    def __on_ttl_changed(self, ttl):
        ttl = int(ttl) if ttl else -1
        self.__item = self.__item._replace(ttl=ttl)
        self.__update()

    def __on_ttl_applied(self):
        if self.ttl_modified:
            item, original_item = self.__item, self.__original_item
            try:
                item.redis.expire(item.key, item.ttl)
                self.__original_item = original_item._replace(ttl=item.ttl)
            except Exception as e:
                print 'error', str(e)
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
        if ttl_modified:
            ttl = self.__item.ttl
            ttl_str = 'Persistent'
            if ttl > 0:
                ttl_str = 'TTL: {0}'.format(timedelta(seconds=ttl))
            ui.ttl_value.setToolTip(ttl_str)

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
        self.ui.ttl_value.setText(str(ttl) if ttl > 0 else '')


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
