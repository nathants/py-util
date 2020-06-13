import socket
import subprocess

def is_port_free(port):
    val = subprocess.check_output(['ss', '-tH']).decode('utf-8')
    return ':{} '.format(port) not in val

def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port_num = sock.getsockname()[1]
    sock.close()
    return port_num
