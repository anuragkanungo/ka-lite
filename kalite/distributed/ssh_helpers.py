#!/usr/bin/env python
import os
import socket
import select
import sys
import threading
import paramiko

from django.conf import settings; logging = settings.LOG


SSH_PORT = 22
DEFAULT_PORT = 4000

def handler(chan, host, port):
    sock = socket.socket()
    try:
        sock.connect((host, port))
    except Exception as e:
        logging.exception('Forwarding request to %s:%d failed: %r' % (host, port, e))
        return
    
    logging.info('Connected!  Tunnel open %r -> %r -> %r' % (chan.origin_addr,
                                                        chan.getpeername(), (host, port)))
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            sock.send(data)
    chan.close()
    sock.close()
    logging.info('Tunnel closed from %r' % (chan.origin_addr,))


def reverse_forward_tunnel(server_port, remote_host, remote_port, transport):
    transport.request_port_forward('', server_port)
    while True:
        chan = transport.accept(1000)
        if chan is None:
            continue
        thr = threading.Thread(target=handler, args=(chan, remote_host, remote_port))
        thr.setDaemon(True)
        thr.start()

def connect():
    
    server = "52.11.120.184", SSH_PORT
    remote = "localhost", 22
    password = "ubuntu"
    username = "ubuntu"
    
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    logging.info('Connecting to ssh host %s:%d ...' % (server[0], server[1]))
    try:
        client.connect(server[0], server[1], username=username, password=password)
    except Exception as e:
        logging.exception('*** Failed to connect to %s:%d: %r' % (server[0], server[1], e))

    logging.info('Now forwarding remote port %d to %s:%d ...' % (DEFAULT_PORT, remote[0], remote[1]))

    try:
        reverse_forward_tunnel(DEFAULT_PORT, remote[0], remote[1], client.get_transport())
    except KeyboardInterrupt:
        sys.exit(0)
