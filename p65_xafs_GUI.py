"""
Last change: Tuesday dec 17 2019

@author: Ruidy Nemausat

"""
import sys
from PyQt5.QtWidgets import QApplication, QWidget


def main():
    app = QApplication(sys.argv)
    w = QWidget()
    w.setWindowTitle("P65 XAFS Scan Manager")
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
