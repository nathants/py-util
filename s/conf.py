from __future__ import print_function, absolute_import
import yaml


def service(name, services_yml='/state/services.yml'):
    with open(services_yml) as f:
        return yaml.safe_load(f)[name]
