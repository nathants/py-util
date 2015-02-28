import s
import re
import requests
import os
import yaml
import boto.ec2


with open(os.path.expanduser('~/.aws')) as f:
    conf = yaml.safe_load(f)


conn = boto.ec2.connect_to_region(**conf['connection'])


def new():
    val = conn.run_instances(**conf['ec2'])
    print(val)


def ls(state='running'):
    for val in conn.get_only_instances(filters={'instance-state-name': state}):
        print(val.id, '|', val.public_dns_name, '|', val.tags)


def kill():
    vals = conn.get_only_instances(filters={'instance-state-name': 'running'})
    print('going to kill:')
    for val in vals:
        print('', val)
    if input('proceed? y/n ') == 'y':
        print('kill...')
        for val in vals:
            val.terminate()


def auth(address=None):
    address = address or requests.get('http://checkip.amazonaws.com').text.strip() + '/32'
    print('adding {address} to ssh security group.\nproceed? y/n'.format(**locals()))
    if input() == 'y':
        print('adding...')
        conn.get_all_security_groups('ssh').pop().authorize('tcp', 22, 22, address)


def auths():
    for rule in conn.get_all_security_groups('ssh').pop().rules:
        for grant in rule.grants:
            print(grant.cidr_ip)


def revoke():
    group = conn.get_all_security_groups('ssh').pop()
    vals = [{'group_id': group.id,
             'ip_protocol': rule.ip_protocol,
             'from_port': rule.from_port,
             'to_port': rule.to_port,
             'cidr_ip': grant.cidr_ip}
            for rule in group.rules
            for grant in rule.grants]
    print('going to revoke ssh access for:')
    for val in vals:
        print('', val['cidr_ip'])
    print('proceed? y/n')
    if input() == 'y':
        for val in vals:
            conn.revoke_security_group(**val)


def main():
    s.shell.dispatch_commands(globals(), __name__)
