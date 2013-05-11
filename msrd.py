#!/usr/bin/env python

import mapper

timeout = 60

monitor = mapper.monitor(enable_autorequest=1)

devices = {}
links = {}
connections = {}

def on_device(dev, action):
    global devices
    if action == mapper.MDB_NEW:
        print 'new device named', dev['name']
        if dev['name'] in devices and 'released' in devices[dev['name']]:
            print 'DEVICE', i['name'], 'RESTARTED!'
            now = monitor.now()
            if now - devices[dev['name']]['released'] < timeout:
                print 'RESTORING LINKS & CONNECTIONS!'
            else:
                print 'FORGETTING LINKS & CONNECTIONS!'
        devices[dev['name']] = dev
    elif action == mapper.MDB_MODIFY:
        devices[dev['name']] = dev
    elif action == mapper.MDB_REMOVE:
        now = monitor.now()
        devices[dev['name']]['released'] = now

def on_link(link, action):
    if action == mapper.MDB_NEW:
        print 'new link'

def on_connection(connection, action):
    if action == mapper.MDB_NEW:
        print 'new connection'

def init_monitor():
    monitor.db.add_device_callback(on_device)
    monitor.db.add_link_callback(on_link)
    monitor.db.add_connection_callback(on_connection)
    monitor.request_devices()

init_monitor()

for j in range(10):
    monitor.poll(1000)
    now = monitor.now()
    for i in monitor.db.all_devices():
        if i['name'] not in devices:
            continue
        synced = i['synced']
        print 'synced', synced, '(', now-synced, ')'
        if synced and now-synced > 5:
            print 'device', i['name'], 'may have crashed!'
            devices[i['name']]['crashed'] = now
        elif 'crashed' in devices[i['name']]:
            del devices[i['name']]['crashed']

