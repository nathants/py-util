import re
import socket
import subprocess

def is_port_free(port):
    val = subprocess.check_output(['netstat', '-pna']).decode('utf-8')
    return ':{} '.format(port) not in val

def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port_num = sock.getsockname()[1]
    sock.close()
    return port_num

def eth0_address(interface='eth0'):
    text = subprocess.check_output(f'ifconfig {interface} | grep "inet"', shell=True).decode('utf-8')
    return re.search(r'inet ([\d\.]+) ', text).group(1)
