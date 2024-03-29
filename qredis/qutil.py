"""QRedis Qt tools"""

import os
import sys
import types
import functools

from qtpy.QtCore import QPoint
from qtpy.QtGui import QPainter, QFont, QColor
from qtpy.uic import loadUi


def add_char_pixmap(pixmap, char, size=14, weight=QFont.Bold):
    """Draw a black character on the pixmap"""
    if len(char) > 1:
        raise ValueError("Only one char is allowed")
    painter = QPainter(pixmap)
    painter.setFont(QFont("Times", size, weight))
    painter.setPen(QColor(255, 0, 0))
    width, height = pixmap.width(), pixmap.height()
    point = QPoint(width - size, height - 2)
    painter.drawText(point, char)


def load_ui(obj, filename=None, path=None, with_ui="ui"):
    """
    Loads a QtDesigner .ui file into the given widget.
    If no filename is given, it tries to load from a file name which is the
    widget class name plus the extension ".ui" (example: if your
    widget class is called MyWidget it tries to find a MyWidget.ui).
    If path is not given it uses the directory where the python file which
    defines the widget is located plus a *ui* directory (example: if your widget
    is defined in a file /home/homer/workspace/my_project/my_widget.py then it uses
    the path /home/homer/workspace/my_project/ui)

    :param filename: the QtDesigner .ui file name [default: None, meaning
                      calculate file name with the algorithm explained before]
    :type filename: str
    :param path: directory where the QtDesigner .ui file is located
                 [default: None, meaning calculate path with algorithm explained
                 before]
    :type path: str
    :param with_ui: if True, the objects defined in the ui file will be
                    accessible as submembers of an ui member of the widget. If
                    False, such objects will directly be members of the widget.
    :type with_ui: bool
    """
    if path is None:
        obj_file = sys.modules[obj.__module__].__file__
        path = os.path.join(os.path.dirname(obj_file), "ui")
    if filename is None:
        filename = obj.__class__.__name__ + os.path.extsep + "ui"
    full_name = os.path.join(path, filename)

    if with_ui is not None:
        ui_obj = types.SimpleNamespace()
        setattr(obj, with_ui, ui_obj)
        previous_members = set(dir(obj))

        loadUi(full_name, baseinstance=obj)

        post_members = set(dir(obj))
        new_members = post_members.difference(previous_members)
        for member_name in new_members:
            member = getattr(obj, member_name)
            setattr(ui_obj, member_name, member)
            delattr(obj, member_name)
    else:
        loadUi(full_name, baseinstance=obj)


def ui_loadable(klass=None, with_ui="ui"):
    """
    A class decorator intended to be used in a Qt.QWidget to make its UI
    loadable from a predefined QtDesigner UI file.
    This decorator will add a :func:`loadUi` method to the decorated class and
    optionaly a property with a name given by *with_ui* parameter.

    The folowing example assumes the existence of the ui file
    :file:`<my_widget_dir>/ui/MyWidget.ui` which is a QWidget panel with *at
    least* a QPushButton with objectName *my_button* ::

        from qtpy import Qt
        from qredis.qutil import ui_loadable

        @ui_loadable
        class MyWidget(Qt.QWidget):

            def __init__(self, parent=None):
                Qt.QWidget.__init__(self, parent)
                self.load_ui()
                self.my_button.setText("This is MY button")

    Another example using a :file:`superUI.ui` file in the same directory as
    the widget. The widget UI components can be accessed through the widget
    member *_ui* ::

        import os.path

        from qtpy import Qt
        from qredis.qutil import ui_loadable

        @ui_loadable(with_ui="_ui")
        class MyWidget(Qt.QWidget):

            def __init__(self, parent=None):
                Qt.QWidget.__init__(self, parent)
                self.load_ui(filename="superUI.ui", path=os.path.dirname(__file__))
                self._ui.my_button.setText("This is MY button")

    :param with_ui: assigns a member to the decorated class from which you
                    can access all UI components [default: None, meaning no
                    member is created]
    :type with_ui: str
    """
    if klass is None:
        return functools.partial(ui_loadable, with_ui=with_ui)

    klass_name = klass.__name__
    klass_file = sys.modules[klass.__module__].__file__
    klass_path = os.path.join(os.path.dirname(klass_file), "ui")

    def _load_ui(self, filename=None, path=None):
        if filename is None:
            filename = klass_name + os.path.extsep + "ui"
        if path is None:
            path = klass_path
        return load_ui(self, filename=filename, path=path, with_ui=with_ui)

    klass.load_ui = _load_ui
    return klass


if __name__ == "__main__":
    from qtpy.QtGui import QIcon
    from qtpy.QtWidgets import QApplication, QLabel

    app = QApplication([])
    i = QIcon.fromTheme("list-add")
    pix = i.pixmap(128, 128)
    add_char_pixmap(pix, "S")
    lbl = QLabel()
    lbl.setPixmap(pix)
    lbl.show()
    app.exec_()
