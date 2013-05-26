#!/usr/bin/env python

import sys
from PySide.QtCore import *
from PySide.QtGui import *
import mashd

crashed_color = QBrush(QColor(200, 0, 0))
active_color = QBrush(QColor(0, 200, 0))
released_color = QBrush(QColor(0, 0, 200))

def timeoutChanged(timeoutString):
    print 'timeout changed to', timeoutString
    #mashd.timeout =

class mashGUI(QMainWindow):
    strict = 1
    
    def __init__(self):
        QMainWindow.__init__(self)
        self.setGeometry(300, 300, 300, 380)
        self.setWindowTitle('Mapping Session Handler')

        self.timeoutLabel1 = QLabel('Timeout:', self)
        self.timeoutLabel1.setGeometry(20, 20, 70, 20)
        self.timeout = QLineEdit('60', self)
        self.timeout.setGeometry(85, 20, 50, 20)
        self.timeout.setAlignment(Qt.AlignRight)
        self.timeout.textChanged.connect(timeoutChanged)
        self.timeoutLabel2 = QLabel('sec', self)
        self.timeoutLabel2.setGeometry(140, 20, 20, 20)

        self.numrows = 0;
        self.deviceTable = QTableWidget(self)
        self.deviceTable.setGeometry(0, 60, 300, 300)
        self.deviceTable.setRowCount(self.numrows)
        self.deviceTable.setColumnCount(2)
        self.deviceTable.setColumnWidth(0, 200)
        self.deviceTable.setColumnWidth(1, 75)
        self.deviceTable.setSelectionMode(QAbstractItemView.NoSelection)
        item = QTableWidgetItem('device name')
        self.deviceTable.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem('status')
        self.deviceTable.setHorizontalHeaderItem(1, item)

        self.label = QLabel(self)
        self.label.setGeometry(20, 355, 260, 30)

        self.timer = QBasicTimer()
        self.timer.start(500, self)

    def timerEvent(self, event):
        if event.timerId() == self.timer.timerId():
            mashd.poll()

            index = 0
            active = 0
            released = 0
            crashed = 0

            if mashd.changed == 0:
                return

            mashd.changed = 0
            self.deviceTable.clearContents()
            for i in mashd.devices:
                while index >= self.numrows:
                    self.numrows += 1
                    self.deviceTable.setRowCount(self.numrows)
                    self.deviceTable.setRowHeight(self.numrows-1, 20)
                item = QTableWidgetItem(mashd.devices[i]['name'])
                self.deviceTable.setItem(index, 0, item)
                item = QTableWidgetItem(mashd.devices[i]['status'])
                self.deviceTable.setItem(index, 1, item)
                if mashd.devices[i]['status'] == 'released':
                    item.setForeground(released_color)
                    released += 1
                elif mashd.devices[i]['status'] == 'crashed':
                    item.setForeground(crashed_color)
                    crashed += 1
                else:
                    active += 1
                    item.setForeground(active_color)
                index += 1
            if index == 0:
                self.numrows = index
                self.deviceTable.setRowCount(self.numrows)
            elif index <= self.numrows:
                self.numrows = index
                self.deviceTable.setRowCount(self.numrows)

            status = "Active: " + str(active) + " | Released: " + str(released) + " | Crashed: " + str(crashed)
            self.label.setText(status)
        else:
            QtGui.QFrame.timerEvent(self, event)

app = QApplication(sys.argv)
mashGUI = mashGUI()
mashGUI.show()
sys.exit(app.exec_())
