#!/usr/bin/env python

import mapper
import argparse

monitor = mapper.monitor(enable_autorequest=1)

parser = argparse.ArgumentParser(description='Automatically restore libmapper network state.')
parser.add_argument('--timeout', dest='timeout', type=int, default=60, help='Timeout after which records are flushed. Links and connections will only be restored if the relevant devices restart before timeout elapses.')

args = parser.parse_args()
timeout = args.timeout

devices = {}
links = {}

def compare_device_class(name1, name2):
    index = name1.find('.', 0)
    left = name1[0:index]
    index = name2.find('.', 0)
    right = name2[0:index]
    return left == right

def restore_links(dev, scenario):
    if scenario not in devices[dev['name']]:
        return
    print 'device', dev['name'], 'restarted', now-devices[dev['name']]['released'], 'seconds after', 'shutting down.' if scenario=='released' else 'crashing.'
    remove = []
    for i in links:
        if compare_device_class(links[i]['src_name'], dev['name']) and links[i]['src_host'] == dev['host']:
            if 'src_'+scenario in links[i]:
                del links[i]['src_'+scenario]
            else:
                continue
            if 'dest_'+scenario not in links[i]:
                print '  relinking', dev['name'], '->', links[i]['dest_name']
                monitor.link(dev['name'], links[i]['dest_name'], links[i])
                for j in links[i]['connections']:
                    print '    reconnecting', links[i]['connections'][j]['src_name'], '->', links[i]['connections'][j]['dest_name']
                    monitor.connect(links[i]['connections'][j]['src_name'], links[i]['connections'][j]['dest_name'], links[i]['connections'][j])
                remove.append(i)
        elif compare_device_class(links[i]['dest_name'], dev['name']) and links[i]['dest_host'] == dev['host']:
            if 'dest_'+scenario in links[i]:
                del links[i]['dest_'+scenario]
            else:
                continue
            if 'src_'+scenario not in links[i]:
                print '  relinking', links[i]['src_name'], '->', dev['name']
                monitor.link(links[i]['src_name'], dev['name'], links[i])
                for j in links[i]['connections']:
                    print '    reconnecting', links[i]['connections'][j]['src_name'], '->', links[i]['connections'][j]['dest_name']
                    monitor.connect(links[i]['connections'][j]['src_name'], links[i]['connections'][j]['dest_name'], links[i]['connections'][j])
                remove.append(i)
    for i in remove:
        del links[i]

def on_device(dev, action):
    now = monitor.now()
    if action == mapper.MDB_NEW:
        if dev['name'] not in devices:
            devices[dev['name']] = dev
            return
        elif 'released' in devices[dev['name']]:
            restore_links(dev, 'released')
        elif 'crashed' in devices[dev['name']]:
            restore_links(dev, 'crashed')
        devices[dev['name']] = dev
    elif action == mapper.MDB_MODIFY:
        if dev['name'] not in devices:
            devices[dev['name']] = dev
        else:
            for i in dev:
                devices[dev['name']][i] = dev[i]
    elif action == mapper.MDB_REMOVE:
        devices[dev['name']]['released'] = now
        for i in links:
            if links[i]['src_name'] == dev['name']:
                links[i]['src_released'] = now
            elif links[i]['dest_name'] == dev['name']:
                links[i]['dest_released'] = now

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
        now = monitor.now()
        links[key]['released'] = now

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
        links[devkey]['connections'][sigkey] = con
    elif action == mapper.MDB_REMOVE:
        if devkey in links and sigkey in links[devkey]['connections']:
            now = monitor.now()
            links[devkey]['connections'][sigkey]['released'] = now

def init_monitor():
    monitor.db.add_device_callback(on_device)
    monitor.db.add_link_callback(on_link)
    monitor.db.add_connection_callback(on_connection)
    monitor.request_devices()

init_monitor()

while 1:
    monitor.poll(1000)
    now = monitor.now()
    for i in monitor.db.all_devices():
        if i['name'] not in devices:
            continue
        synced = i['synced']
        if synced:
            if now-synced > 11:
                print 'device', i['name'], 'may have crashed! (', now-synced, 'sec timeout)'
                devices[i['name']]['crashed'] = now
            elif 'crashed' in devices[i['name']]:
                del devices[i['name']]['crashed']
    remove = [k for k in devices if 'released' in devices[k] and now-devices[k]['released'] > timeout]
    for k in remove:
        print 'timeout: forgetting released device', devices[k]['name']
        del devices[k]
    remove = [k for k in devices if 'crashed' in devices[k] and now-devices[k]['crashed'] > timeout]
    for k in remove:
        print 'timeout: forgetting crashed device', devices[k]['name']
        del devices[k]
