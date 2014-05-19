import s
import socket


def port_free(port):
    return ':{} '.format(port) not in s.shell.run('netstat -lpn')


def free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 0))
    port_num = sock.getsockname()[1]
    sock.close()
    return port_num
