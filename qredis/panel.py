from .qt import Qt, QSplitter
from .tree import RedisTree
from .editor import RedisEditor


class RedisPanel(QSplitter):
    def __init__(self, parent=None):
        super(RedisPanel, self).__init__(parent)
        self.tree = RedisTree(self)
        self.editor = RedisEditor(self)
        self.tree.setWindowFlags(Qt.Widget)
        self.addWidget(self.tree)
        self.addWidget(self.editor)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 1)
        self.tree.selectionChanged.connect(self.__on_selection_changed)

    def __on_selection_changed(self, selected):
        all_items = selected['all_items']
        if len(all_items) == 1:
            db_items = selected['db_items']
            if db_items:
                self.editor.set_db(db_items[0].redis)
                return
            key_items = selected['key_items']
            if key_items:
                key_item = key_items[0]
                if key_item.has_value:
                    self.editor.set_item(key_item.redis, key_item.key)
                    return
        self.editor.set_empty()

    def add_redis(self, redis):
        self.tree.add_redis(redis)
