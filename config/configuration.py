import yaml


def resolve_yaml_config(config_file):
    config = yaml.safe_load(config_file)
    return config
