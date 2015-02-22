from __future__ import print_function, absolute_import
import yaml
import s


def service(name, services_yml='/state/services.yml', default=None):
    with s.exceptions.ignore():
        with open(services_yml) as f:
            return yaml.safe_load(f)[name]
    return default
