import re
import socket
import subprocess

import s.hacks


def is_port_free(port):
    val = subprocess.check_output(['netstat', '-pna'])
    return ':{} '.format(port) not in s.hacks.stringify(val)


def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port_num = sock.getsockname()[1]
    sock.close()
    return port_num


def eth0_address():
    text = subprocess.check_output('ifconfig eth0 | grep "inet addr"', shell=True)
    return re.search('inet addr:([\d\.]+) ', text).group(1)
