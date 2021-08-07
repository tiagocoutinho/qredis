import os
import logging

from .qt import QMainWindow, QApplication, QIcon, QActionGroup, QMdiArea, Qt, ui_loadable
from .util import restart, redis_str
from .redis import QRedis
from .panel import RedisPanel
from .dialog import AboutDialog, OpenRedisDialog


_redis_icon = os.path.join(os.path.dirname(__file__), "images", "redis_logo.png")


@ui_loadable
class RedisWindow(QMainWindow):
    def __init__(self, parent=None):
        super(RedisWindow, self).__init__(parent)
        self.load_ui()
        ui = self.ui
        redis_icon = QIcon(_redis_icon)
        self.setWindowIcon(redis_icon)
        self.about_dialog = AboutDialog()

        ui.open_db_action.setIcon(redis_icon)
        ui.open_db_action.triggered.connect(self._on_open_db)
        ui.restart_action.triggered.connect(restart)
        ui.quit_action.triggered.connect(QApplication.quit)
        ui.about_action.triggered.connect(lambda: self.about_dialog.exec_())

        ui.window_mode_action_group = group = QActionGroup(self)
        ui.tabbed_view_action.setActionGroup(group)
        ui.tabbed_view_action.setData(QMdiArea.TabbedView)
        ui.window_view_action.setActionGroup(group)
        ui.window_view_action.setData(QMdiArea.SubWindowView)
        group.triggered.connect(self._on_switch_window_mode)
        self.set_view_mode(QMdiArea.TabbedView)
        ui.tabbed_view_action.setChecked(True)

    def _on_open_db(self):
        redis, opts = OpenRedisDialog.create_redis(parent=self)
        if redis:
            self.add_redis_panel(redis, opts)

    def set_view_mode(self, mode):
        mdi = self.ui.mdi
        mdi.setViewMode(mode)
        self.ui.cascade_action.setEnabled(mode != QMdiArea.TabbedView)
        self.ui.tile_action.setEnabled(mode != QMdiArea.TabbedView)

    def _on_switch_window_mode(self, action):
        mode = action.data()
        self.set_view_mode(mode)

    def add_redis_panel(self, redis, opts):
        name, _ = redis_str(redis)
        panel = RedisPanel(redis)
        window = self.ui.mdi.addSubWindow(panel)
        window.setAttribute(Qt.WA_DeleteOnClose)
        window.setWindowTitle(name)
        window.setVisible(True)
        window.showMaximized()
        self.ui.mdi.setActiveSubWindow(window)
        return window


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="QRedis GUI")
    parser.add_argument("--host", help="Server host name")
    parser.add_argument("-p", "--port", help="Server port", type=int)
    parser.add_argument("-s", "--sock", help="unix server socket")
    parser.add_argument("-n", "--db", type=int, help="Database number")
    parser.add_argument("--name", default="qredis", help="Client name")
    parser.add_argument("-f", "--key-filter", default="*", help="Key filter")
    parser.add_argument("--key-split", default=".:", help="Key splitter")
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

    kwargs = dict(client_name=args.name)
    if args.host is not None:
        kwargs["host"] = args.host
    if args.port is not None:
        kwargs["port"] = args.port
    if args.sock is not None:
        kwargs["unix_socket_path"] = args.sock
    if args.db is not None:
        kwargs["db"] = args.db
    opts = dict(filter=args.key_filter, split_by=args.key_split)
    application = QApplication(sys.argv)
    window = RedisWindow()
    if len(kwargs) > 1:
        r = QRedis(**kwargs)
        window.add_redis_panel(r, opts)
    window.show()
    sys.exit(application.exec_())


if __name__ == "__main__":
    main()
