# -*- coding: utf-8 -*-
"""Qt wrapper"""

__V = 4
try:
    import PyQt4
except ImportError:
    __V = 5


if __V == 4:
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)
    from PyQt4 import Qt
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    from PyQt4.QtSvg import *
    from PyQt4.uic import *
else:
    from PyQt5 import Qt
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtSvg import *
    from PyQt5.QtWidgets import *
    from PyQt5.uic import *
