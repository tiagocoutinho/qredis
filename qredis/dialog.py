from .redis import QRedis
from .qt import QDialog, QRegExpValidator, QRegExp, ui_loadable


@ui_loadable
class OpenRedisDialog(QDialog):

    Dialog = None

    def __init__(self, parent=None):
        """Display a dialog to open a new redis connection"""
        super(OpenRedisDialog, self).__init__(parent)
        self.load_ui()
        v = QRegExpValidator(QRegExp("([^:/]+)?(:[0-9]+)?"))
        self.ui.tcp.setValidator(v)
        self.ui.tcp_option.setChecked(True)

    def _create_redis(self):
        if self.exec_() != QDialog.Accepted:
            return None, None
        kwargs = dict(db=self.ui.db.value())
        client_name = self.ui.name.text()
        user = self.ui.user.text()
        password = self.ui.password.text()
        if client_name:
            kwargs["client_name"] = client_name
        if user:
            kwargs["username"] = user
        if password:
            kwargs["password"] = password
        if self.ui.tcp_option.isChecked():
            url = self.ui.tcp.text()
            if ":" in url:
                host, port = url.split(":")
                if port:
                    kwargs["port"] = int(port)
            else:
                host = url
            if host:
                kwargs["host"] = host
        else:
            kwargs["unix_socket_path"] = self.ui.socket.text()
        opts = dict(
            filter=self.ui.filter.text(),
            split_by=self.ui.splitter.text(),
        )
        return QRedis(**kwargs), opts

    @classmethod
    def create_redis(cls, parent=None):
        if cls.Dialog is None:
            cls.Dialog = cls(parent=parent)
        return cls.Dialog._create_redis()


class AboutDialog(QDialog):
    """Create the necessary elements to show helpful text in a dialog."""

    def __init__(self, parent=None):
        """Display a dialog that shows application information."""
        super(AboutDialog, self).__init__(parent)
        self.setWindowTitle("About")
