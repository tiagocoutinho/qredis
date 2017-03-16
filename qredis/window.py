import os
import sys
import logging

from .qt import Qt, QMainWindow, QApplication, QDialog, QLabel, \
                QTreeWidget, QTreeWidgetItem, QMessageBox, \
                QIcon, QFont, QMenu, QAction, QSize, QPoint, QKeySequence, \
                QRegExpValidator, QRegExp, \
                ui_loadable
from .tree import RedisTree
from .dialog import AboutDialog


_this_dir = os.path.dirname(__file__)
_res_dir = os.path.join(_this_dir, 'images')
_redis_icon = os.path.join(_res_dir, 'redis_logo.png')

_startup_cwd = os.getcwd()

def restart():
    if 'linux' in sys.platform.lower():
        with open('/proc/{0}/cmdline'.format(os.getpid())) as f:
            args = [arg for arg in f.read().split('\x00') if arg]
            executable = args[0]
    else:
        args = sys.argv[:]
        executable = sys.executable

    os.chdir(_startup_cwd)
    os.execvp(executable, args)

@ui_loadable
class RedisWindow(QMainWindow):

    def __init__(self, parent=None):
        super(RedisWindow, self).__init__(parent)
        self.load_ui()
        ui = self.ui
        redis_icon = QIcon(_redis_icon)
        self.setWindowIcon(redis_icon)
        self.about_dialog = AboutDialog()
        self.tree = RedisTree(self)
        self.tree.setWindowFlags(Qt.Widget)
        self.setCentralWidget(self.tree)

        ui.restart_action.triggered.connect(restart)
        ui.quit_action.triggered.connect(QApplication.quit)
        ui.about_action.triggered.connect(lambda: self.about_dialog.exec_())

    def status_message(self, msg, timeout=0):
        self.statusBar().showMessage(msg, int(timeout*1000.))


def main():
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
        import redis
        r = redis.Redis(**kwargs)
        window.tree.add_redis(r)
    window.show()
    sys.exit(application.exec_())


if __name__ == '__main__':
    main()
