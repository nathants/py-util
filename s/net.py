from __future__ import print_function, absolute_import
import s
import socket
import re


def port_free(port):
    return ':{} '.format(port) not in s.shell.run('netstat -pna')


def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port_num = sock.getsockname()[1]
    sock.close()
    return port_num


def eth0_address():
    text = s.shell.run('ifconfig eth0 | grep "inet addr"')
    return re.search('inet addr:([\d\.]+) ', text).group(1)
