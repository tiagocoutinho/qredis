import os
import logging

from .qt import QMainWindow, QApplication, QIcon, ui_loadable
from .util import restart
from .redis import QRedis
from .panel import RedisPanel
from .dialog import AboutDialog, OpenRedisDialog


_redis_icon = os.path.join(os.path.dirname(__file__), 'images', 'redis_logo.png')


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
        ui.open_db_action.triggered.connect(self.__on_open_db)
        ui.restart_action.triggered.connect(restart)
        ui.quit_action.triggered.connect(QApplication.quit)
        ui.about_action.triggered.connect(lambda: self.about_dialog.exec_())
        ui.tab_windows_action.toggled.connect(self.__on_tab_toggled)

    def __on_open_db(self):
        redis = OpenRedisDialog.create_redis()
        if redis:
            self.add_redis_panel(redis)

    def __on_tab_toggled(self, checked):
        mdi = self.ui.mdi
        mdi.setViewMode(mdi.TabbedView if checked else mdi.SubWindowView)

    def add_redis_panel(self, *redis):
        panel = RedisPanel(parent=self)
        for r in redis:
            panel.add_redis(r)
        window = self.ui.mdi.addSubWindow(panel)
        window.setWindowTitle('Redis')
        if len(self.ui.mdi.subWindowList()) == 1:
            window.showMaximized()
        return window


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='QRedis GUI')
    parser.add_argument('--host', help='Server host name')
    parser.add_argument('-p', '--port', help='Server port', type=int)
    parser.add_argument('-s', '--sock', help='unix server socket')
    parser.add_argument('-n', '--db', help='Database number')
    parser.add_argument('--log-level', default='WARNING', help='log level',
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'])
    args = parser.parse_args()

    fmt = '%(asctime)-15s %(levelname)-5s %(name)s: %(message)s'
    level = getattr(logging, args.log_level.upper())
    logging.basicConfig(format=fmt, level=level)

    kwargs = {}
    if args.host is not None:
        kwargs['host'] = args.host
    if args.port is not None:
        kwargs['port'] = args.port
    if args.sock is not None:
        kwargs['unix_socket_path'] = args.sock
    application = QApplication(sys.argv)
    window = RedisWindow()
    if kwargs:
        r = QRedis(**kwargs)
        window.add_redis_panel(r)
    window.show()
    sys.exit(application.exec_())


if __name__ == '__main__':
    main()
