#!/usr/bin/env python

import mapper

devices = {}
links = {}
monitor = mapper.monitor(autorequest=mapper.AUTOREQ_LINKS | mapper.AUTOREQ_CONNECTIONS)
relaunch_same_host = 1
timeout = 60
now = 0
changed = 0

id_counter = 0;

def poll(wait=0):
    monitor.poll(wait)
    check_devices()

def increment_id_counter():
    global id_counter
    id_counter += 1
    if id_counter < 0:
        id_counter = 0

def get_device_class(name):
    return name[0:name.find('.', 0)]

def lookup_device(name):
    for i in devices:
        if devices[i]['name'] == name:
            return i
    return -1

def split_sig_name(name):
    index = name.find('/', 1)
    dev = name[0:index]
    sig = name[index:]
    return [dev, sig]

def restore_links(dev_id):
    now = monitor.now()
    # find most recently released of possible matches
    dev_class = get_device_class(devices[dev_id]['name'])
    dev_host = devices[dev_id]['host']
    match = -1
    for i in devices:
        if i == dev_id:
            continue
        elif devices[i]['status'] == 'active':
            continue
        elif dev_class != get_device_class(devices[i]['name']):
            continue
        elif relaunch_same_host and devices[i]['host'] != dev_host:
            continue
        elif match < 0 or devices[i]['synced'] > devices[match]['synced']:
            match = i
    if match == -1:
        return
    print 'mashd: device', devices[match]['name'], 'restarted as', devices[dev_id]['name'], 'after', now-devices[match]['synced'], 'seconds.'

    restored_links = []
    for i in links:
        if 'src_released' in links[i] and links[i]['src_id'] == match:
            if 'dest_released' in links[i]:
                links[i]['src_name'] = devices[dev_id]['name']
                links[i]['src_id'] = dev_id
                del links[i]['src_released']
            else:
                print 'mashd: relinking', devices[dev_id]['name'], '->', links[i]['dest_name']
                monitor.link(devices[dev_id]['name'], links[i]['dest_name'], links[i])
                for j in links[i]['connections']:
                    print 'mashd: reconnecting', devices[dev_id]['name']+links[i]['connections'][j]['src_name'], '->', links[i]['dest_name']+links[i]['connections'][j]['dest_name']
                    monitor.connect(devices[dev_id]['name']+links[i]['connections'][j]['src_name'], links[i]['dest_name']+links[i]['connections'][j]['dest_name'], links[i]['connections'][j])
                restored_links.append(i)
        elif 'dest_released' in links[i] and links[i]['dest_id'] == match:
            if 'src_released' in links[i]:
                links[i]['name'] = devices[dev_id]['name']
                links[i]['dest_id'] = dev_id
                del links[i]['dest_released']
            else:
                print 'mashd: relinking', links[i]['src_name'], '->', devices[dev_id]['name']
                monitor.link(links[i]['src_name'], devices[dev_id]['name'], links[i])
                for j in links[i]['connections']:
                    print 'mashd: reconnecting', links[i]['src_name']+links[i]['connections'][j]['src_name'], '->', devices[dev_id]['name']+links[i]['connections'][j]['dest_name']
                    monitor.connect(links[i]['src_name']+links[i]['connections'][j]['src_name'], devices[dev_id]['name']+links[i]['connections'][j]['dest_name'], links[i]['connections'][j])
                restored_links.append(i)
    for i in restored_links:
        del links[i]

    # Remove old device record
    del devices[match]

def remove_expired_links(dev_id):
    expired = [k for k in links if links[k]['src_id'] == dev_id or links[k]['dest_id'] == dev_id]
    for k in expired:
        del links[k]

def on_device(dev, action):
    global changed, id_counter
    changed = 1
    now = monitor.now()
    if action == mapper.MDB_NEW:
        print 'new device:', dev['name'], '(', id_counter, ')'
        devices[id_counter] = dev
        devices[id_counter]['status'] = 'active'
        devices[id_counter]['synced'] = now
        restore_links(id_counter)
        increment_id_counter()
    elif action == mapper.MDB_REMOVE:
        found = lookup_device(dev['name'])
        if found == -1:
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
            del devices[found]
        else:
            devices[found]['status'] = 'released'
            devices[found]['synced'] = now
        
def on_link(link, action):
    global changed
    changed = 1
    key = link['src_name'] + '>' + link['dest_name']
    src = lookup_device(link['src_name'])
    dest = lookup_device(link['dest_name'])
    if action == mapper.MDB_NEW:
        link['connections'] = {}
        link['src_id'] = src
        link['dest_id'] = dest
        link['src_host'] = devices[src]['host']
        link['dest_host'] = devices[dest]['host']
        links[key] = link
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
        if key in links and 'connections' in links[key]:
            for i in links[key]['connections']:
                if 'released' in links[key]['connections'][i]:
                    del links[key]['connections'][i]['released']
        links[key]['released'] = monitor.now()

def on_connection(con, action):
    global changed
    changed = 1
    [srcdev, srcsig] = split_sig_name(con['src_name'])
    [destdev, destsig] = split_sig_name(con['dest_name'])
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
        if devkey in links and sigkey in links[devkey]['connections']:
            links[devkey]['connections'][sigkey]['released'] = monitor.now()

def init_monitor():
    monitor.db.add_device_callback(on_device)
    monitor.db.add_link_callback(on_link)
    monitor.db.add_connection_callback(on_connection)
    monitor.request_devices()

def check_devices():
    global changed
    now = monitor.now()
    for dev in monitor.db.all_devices():
        found = lookup_device(dev['name'])
        if found == -1:
            on_device(dev, mapper.MDB_NEW)
            continue
        synced = dev['synced']
        if synced:
            if now-synced > 11:
                if devices[found]['status'] == 'active':
                    print 'mashd: device', dev['name'], 'may have crashed! (', now-synced, 'sec timeout)'
                    devices[found]['status'] = 'crashed'
                    changed = 1
            elif devices[found]['status'] != 'active':
                devices[found]['status'] = 'active'
                devices[found]['synced'] = now
                changed = 1
    expired = [i for i in devices if devices[i]['status'] != 'active' and now-devices[i]['synced'] > timeout]
    if expired:
        changed = 1
    for i in expired:
        print 'mashd: forgetting released device', devices[i]['name'], 'after', now-devices[i]['synced'], 'seconds.'
        remove_expired_links(i)
        del devices[i]
    expired = [i for i in links if 'released' in links[i] and now-links[i]['released'] > 2]
    if expired:
        changed = 1
    for i in expired:
        del links[i]
    for i in links:
        expired = [j for j in links[i]['connections'] if 'released' in links[i]['connections'][j] and now-links[i]['connections'][j]['released'] > 2]
        if expired:
            changed = 1
        for j in expired:
            del links[i]['connections'][j]

init_monitor()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Automatically restore libmapper network state.')
    parser.add_argument('--timeout', dest='timeout', type=int, default=60, help='Timeout after which records are flushed. Links and connections will only be restored if the relevant devices restart before timeout elapses (default 60).')
    parser.add_argument('--same_host', dest='same_host', type=int, default=1, help='Only handle device relaunches on same host computer as released device (default 1).')

    args = parser.parse_args()
    timeout = args.timeout
    relaunch_same_host = args.same_host

    while 1:
        poll(1000)
