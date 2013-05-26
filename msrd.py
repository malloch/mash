#!/usr/bin/env python

import sys
from PySide.QtCore import *
from PySide.QtGui import *
import mapper

devices = {}
links = {}
monitor = mapper.monitor(enable_autorequest=1)
relaunch_same_host = 1
timeout = 30
now = 0

def timeoutChanged(timeoutString):
    print 'timeout changed to', timeoutString

class msrd(QMainWindow):
    strict = 1
    
    def __init__(self):
        QMainWindow.__init__(self)
        self.setGeometry(300, 300, 300, 380)
        self.setWindowTitle('Mapping Session Handler')
        #strict_button = QCheckBox("Only support relaunch on same computer.")
        #strict_button.clicked.connect(set_strict)
        #strict_button.show()

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
        item = QTableWidgetItem('device name')
        self.deviceTable.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem('status')
        self.deviceTable.setHorizontalHeaderItem(1, item)

        self.label = QLabel(self)
        self.label.setGeometry(20, 355, 260, 30)

        self.timer = QBasicTimer()
        self.timer.start(1000, self)

    def timerEvent(self, event):
        if event.timerId() == self.timer.timerId():
            monitor.poll(10)
            check_devices()

            index = 0
            active = 0
            released = 0
            crashed = 0

            self.deviceTable.clearContents()
            for i in devices:
                while index >= self.numrows:
                    self.numrows += 1
                    self.deviceTable.setRowCount(self.numrows)
                    self.deviceTable.setRowHeight(self.numrows-1, 20)
                item = QTableWidgetItem(devices[i]['name'])
                self.deviceTable.setItem(index, 0, item)
                item = QTableWidgetItem(devices[i]['status'])
                self.deviceTable.setItem(index, 1, item)
                if devices[i]['status'] == 'released':
                    released += 1
                elif devices[i]['status'] == 'crashed':
                    crashed += 1
                else:
                    active += 1
                index += 1
            if index == 0:
                self.numrows = index
                self.deviceTable.setRowCount(self.numrows)
            elif index <= self.numrows:
                self.numrows = index + 1
                self.deviceTable.setRowCount(self.numrows)

            status = "Active: " + str(active) + " | Released: " + str(released) + " | Crashed: " + str(crashed)
            self.label.setText(status)
        else:
            QtGui.QFrame.timerEvent(self, event)

def get_device_class(name):
    return name[0:name.find('.', 0)]

def restore_links(dev):
    now = monitor.now()
    # find most recently released of possible matches
    match = None
    for i in devices:
        if devices[i]['status'] == 'active':
            continue
        if get_device_class(dev['name']) != get_device_class(devices[i]['name']):
            continue
        if relaunch_same_host and devices[i]['host'] != dev['host']:
            continue
        if not match or devices[i]['synced'] > match['synced']:
            match = devices[i]
    if not match:
        return
    print 'mashd: device', dev['name'], 'restarted as', match['name'], 'after', now-match['synced'], 'seconds.'

    restored_links = []
    for i in links:
        if 'src_released' in links[i] and links[i]['src_name'] == match['name']:
            if 'dest_released' in links[i]:
                links[i]['src_name'] = dev['name']
                del links[i]['src_released']
            else:
                print '  relinking', dev['name'], '->', links[i]['dest_name']
                monitor.link(dev['name'], links[i]['dest_name'], links[i])
                for j in links[i]['connections']:
                    print '    reconnecting', dev['name']+links[i]['connections'][j]['src_name'], '->', links[i]['dest_name']+links[i]['connections'][j]['dest_name']
                    monitor.connect(dev['name']+links[i]['connections'][j]['src_name'], links[i]['dest_name']+links[i]['connections'][j]['dest_name'], links[i]['connections'][j])
                restored_links.append(i)
        elif 'dest_released' in links[i] and links[i]['dest_name'] == match['name']:
            if 'src_released' in links[i]:
                links[i]['name'] = dev['name']
                del links[i]['dest_released']
            else:
                print '  relinking', links[i]['src_name'], '->', dev['name']
                monitor.link(links[i]['src_name'], dev['name'], links[i])
                for j in links[i]['connections']:
                    print '    reconnecting', links[i]['src_name']+links[i]['connections'][j]['src_name'], '->', dev['name']+links[i]['connections'][j]['dest_name']
                    monitor.connect(links[i]['src_name']+links[i]['connections'][j]['src_name'], dev['name']+links[i]['connections'][j]['dest_name'], links[i]['connections'][j])
                restored_links.append(i)
    for i in restored_links:
        del links[i]

def remove_expired_links(name):
    expired = [k for k in links if links[k]['src_name'] == name or links[k]['dest_name'] == name]
    for k in expired:
        del links[k]

def on_device(dev, action):
    now = monitor.now()
    if action == mapper.MDB_NEW:
        restore_links(dev)
        devices[dev['name']] = dev
        devices[dev['name']]['status'] = 'active'
        devices[dev['name']]['synced'] = now
    elif action == mapper.MDB_MODIFY:
        if dev['name'] not in devices:
            devices[dev['name']] = dev
        else:
            for i in dev:
                devices[dev['name']][i] = dev[i]
    elif action == mapper.MDB_REMOVE:
        if dev['name'] not in devices:
            return
        outgoing_links = [k for k in links if links[k]['src_name'] == dev['name']]
        for k in outgoing_links:
            if 'released' in links[k]:
                del links[k]['released']
            links[k]['src_released'] = now
        incoming_links = [k for k in links if links[k]['dest_name'] == dev['name']]
        for k in incoming_links:
            if 'released' in links[k]:
                del links[k]['released']
            links[k]['dest_released'] = now
        if not outgoing_links and not incoming_links:
            del devices[dev['name']]
        else:
            devices[dev['name']]['status'] = 'released'
            devices[dev['name']]['synced'] = now
        
def on_link(link, action):
    key = link['src_name'] + '>' + link['dest_name']
    if action == mapper.MDB_NEW:
        links[key] = link
        links[key]['connections'] = {}
        links[key]['src_host'] = devices[link['src_name']]['host']
        links[key]['dest_host'] = devices[link['dest_name']]['host']
    elif action == mapper.MDB_MODIFY:
        for i in link:
            links[key][i] = link[i]
    elif action == mapper.MDB_REMOVE:
        '''
        When a device logs out, its child links are removed
        from the monitor.db first. In this case we would like
        to keep our archive of the link until the timeout period
        has elapsed, but we want to remove it if a user removed
        the link individually. To accomplish this we will briefly
        store all released links and check if the parent device is
        released immediately afterwards.
        '''
        for i in links[key]['connections']:
            if 'released' in links[key]['connections'][i]:
                del links[key]['connections'][i]['released']
        links[key]['released'] = monitor.now()

def on_connection(con, action):
    index = con['src_name'].find('/', 1)
    srcdev = con['src_name'][0:index]
    srcsig = con['src_name'][index:]
    index = con['dest_name'].find('/', 1)
    destdev = con['dest_name'][0:index]
    destsig = con['dest_name'][index:]
    devkey = srcdev + '>' + destdev
    sigkey = srcsig + '>' + destsig
    if action == mapper.MDB_NEW or action == mapper.MDB_MODIFY:
        con['src_name'] = srcsig
        con['dest_name'] = destsig
        links[devkey]['connections'][sigkey] = con
    elif action == mapper.MDB_REMOVE:
        '''
        When a device logs out, its child connections are removed
        from the monitor.db first. In this case we would like
        to keep our archive of the connection until the timeout period
        has elapsed, but we want to remove it if a user removed
        the connection individually. To accomplish this we will briefly
        store all released connections and check if the parent link
        or device is released immediately afterwards.
        '''
        links[devkey]['connections'][sigkey]['released'] = monitor.now()

def init_monitor():
    monitor.db.add_device_callback(on_device)
    monitor.db.add_link_callback(on_link)
    monitor.db.add_connection_callback(on_connection)
    monitor.request_devices()

init_monitor()

def resync_monitor():
    print 'resync!'

def set_strict():
    print 'set strict!'

def check_devices():
    now = monitor.now()
    for i in monitor.db.all_devices():
        if i['name'] not in devices:
            continue
        synced = i['synced']
        if synced:
            if now-synced > 11:
                print 'mashd: device', i['name'], 'may have crashed! (', now-synced, 'sec timeout)'
                devices[i['name']]['status'] = 'crashed'
            elif devices[i['name']]['status'] == 'crashed':
                devices[i['name']]['status'] = 'active'
    expired = [i for i in devices if devices[i]['status'] != 'active' and now-devices[i]['synced'] > timeout]
    for i in expired:
        print 'timeout: forgetting released device', devices[i]['name']
        remove_expired_links(devices[i]['name'])
        del devices[i]
    expired = [i for i in links if 'released' in links[i] and now-links[i]['released'] > 2]
    for i in expired:
        del links[i]
    for i in links:
        expired = [j for j in links[i]['connections'] if 'released' in links[i]['connections'][j] and now-links[i]['connections'][j]['released'] > 2]
        for j in expired:
            del links[i]['connections'][j]

app = QApplication(sys.argv)
msrd = msrd()
msrd.show()
sys.exit(app.exec_())
