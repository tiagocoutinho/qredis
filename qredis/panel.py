from .qt import Qt, QSplitter
from .tree import RedisTree
from .editor import RedisEditor


class RedisPanel(QSplitter):
    def __init__(self, redis, parent=None):
        super(RedisPanel, self).__init__(parent)
        self.redis = redis
        self.tree = RedisTree(redis, parent=self)
        self.editor = RedisEditor(self)
        self.tree.setWindowFlags(Qt.Widget)
        self.addWidget(self.tree)
        self.addWidget(self.editor)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 1)
        self.tree.currentChanged.connect(self.__on_selection_changed)
        self.tree.addKey.connect(self.editor.set_item)

    def __on_add_key(self, item):
        self.editor.set_item(item)

    def __on_selection_changed(self, node):
        if node is None:
            self.editor.set_empty()
        elif node.is_key():
            item = self.redis.get(node.key)
            self.editor.set_item(item)
        elif node.is_db():
            self.editor.set_db(self.redis)
