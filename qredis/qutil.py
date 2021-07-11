from .qt import QPainter, QPoint, QFont, QColor


def add_char_pixmap(pixmap, char, size=14, weight=QFont.Bold):
    if len(char) > 1:
        raise ValueError("Only one char is allowed")
    painter = QPainter(pixmap)
    painter.setFont(QFont("Times", size, weight))
    painter.setPen(QColor(255, 0, 0))
    w, h = pixmap.width(), pixmap.height()
    p = QPoint(w - size, h - 2)
    painter.drawText(p, char)


if __name__ == "__main__":
    from .qt import QApplication, QLabel, QIcon

    app = QApplication([])
    i = QIcon.fromTheme("list-add")
    p = i.pixmap(128, 128)
    add_char_pixmap(p, "S")
    lbl = QLabel()
    lbl.setPixmap(p)
    lbl.show()
    app.exec_()
