import os
import logging

from .qt import QMainWindow, QApplication, QIcon, ui_loadable
from .util import restart
from .redis import QRedis
from .panel import RedisPanel
from .dialog import AboutDialog

_redis_icon = os.path.join(os.path.dirname(__file__), 'images', 'redis_logo.png')


@ui_loadable
class RedisWindow(QMainWindow):

    def __init__(self, parent=None):
        super(RedisWindow, self).__init__(parent)
        self.load_ui()
        ui = self.ui
        self.setWindowIcon(QIcon(_redis_icon))
        self.about_dialog = AboutDialog()
        self.panel = RedisPanel(parent=self)
        self.setCentralWidget(self.panel)

        ui.restart_action.triggered.connect(restart)
        ui.quit_action.triggered.connect(QApplication.quit)
        ui.about_action.triggered.connect(lambda: self.about_dialog.exec_())

    def status_message(self, msg, timeout=0):
        self.statusBar().showMessage(msg, int(timeout*1000.))

    def add_redis(self, redis):
        self.panel.add_redis(redis)


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
        window.add_redis(r)
    window.show()
    sys.exit(application.exec_())


if __name__ == '__main__':
    main()
