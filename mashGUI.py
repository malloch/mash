#!/usr/bin/env python

import sys
from PySide.QtCore import *
from PySide.QtGui import *
import mashd

crashed_color = QBrush(QColor(200, 0, 0))
active_color = QBrush(QColor(0, 200, 0))
released_color = QBrush(QColor(0, 0, 200))

timeoutTemp = 60
timeoutValidator = QIntValidator()
timeoutValidator.setBottom(1)

def timeoutChanged(timeoutString):
    global timeoutTemp
    if timeoutString:
        timeoutTemp = int(timeoutString)


def timeoutEntered():
    global timeoutTemp
    if timeoutTemp and timeoutTemp > 0:
        mashd.timeout = timeoutTemp

def relaunchSameHostChanged(state):
    mashd.relaunch_same_host = 1 if state else 0

class mashGUI(QMainWindow):
    strict = 1
    
    def __init__(self):
        QMainWindow.__init__(self)
        self.setGeometry(300, 300, 500, 380)
        self.setFixedSize(500, 300)
        self.setWindowTitle('Mapping Session Handler')

        self.timeoutLabel1 = QLabel('Time window for device restart:', self)
        self.timeoutLabel1.setGeometry(5, 10, 250, 10)
        self.timeout = QLineEdit('60', self)
        self.timeout.setValidator(timeoutValidator)
        self.timeout.setGeometry(210, 5, 55, 20)
        self.timeout.setAlignment(Qt.AlignRight)
        self.timeout.textChanged.connect(timeoutChanged)
        self.timeout.editingFinished.connect(timeoutEntered)
        self.timeout.setFocusPolicy(Qt.ClickFocus)
        self.timeout.clearFocus()
        self.timeoutLabel2 = QLabel('sec', self)
        self.timeoutLabel2.setGeometry(270, 5, 20, 20)

        self.separator = QLabel(self)
        self.separator.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.separator.setGeometry(5, 30, 290, 2)

        self.relaunchSameHost = QCheckBox('Devices must relaunch on same host.', self)
        self.relaunchSameHost.setGeometry(5, 36, 260, 20)
        self.relaunchSameHost.setChecked(1)
        self.relaunchSameHost.stateChanged.connect(relaunchSameHostChanged)

        self.numrows = 0;
        self.deviceTable = QTableWidget(self)
        self.deviceTable.setGeometry(0, 60, 500, 300)
        self.deviceTable.setRowCount(self.numrows)
        self.deviceTable.setColumnCount(4)
        self.deviceTable.setColumnWidth(0, 50)
        self.deviceTable.setColumnWidth(1, 175)
        self.deviceTable.setColumnWidth(2, 175)
        self.deviceTable.setColumnWidth(3, 75)
        self.deviceTable.setSelectionMode(QAbstractItemView.NoSelection)
        item = QTableWidgetItem('mpid')
        self.deviceTable.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem('device name')
        self.deviceTable.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem('host')
        self.deviceTable.setHorizontalHeaderItem(2, item)
        item = QTableWidgetItem('status')
        self.deviceTable.setHorizontalHeaderItem(3, item)

        self.statusLabel = QLabel('Active: 0, Released: 0, Crashed: 0', self)
        self.statusLabel.setGeometry(5, 355, 260, 30)

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
                item = QTableWidgetItem('%i' %i)
                self.deviceTable.setItem(index, 0, item)
                item = QTableWidgetItem(mashd.devices[i]['name'])
                self.deviceTable.setItem(index, 1, item)
                item = QTableWidgetItem(mashd.devices[i]['host'])
                self.deviceTable.setItem(index, 2, item)
                item = QTableWidgetItem(mashd.devices[i]['status'])
                self.deviceTable.setItem(index, 3, item)
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
            self.statusLabel.setText(status)
        else:
            QtGui.QFrame.timerEvent(self, event)

app = QApplication(sys.argv)
mashGUI = mashGUI()
mashGUI.show()
sys.exit(app.exec_())
