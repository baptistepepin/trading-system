import yaml
import os
import re


def resolve_yaml_config(config_file):

    config = yaml.safe_load(config_file)

    env_var_pattern = re.compile(r'\$\{([A-Za-z0-9_]+)\}')

    def replace_env_variables(item):
        if isinstance(item, dict):
            for key, value in item.items():
                item[key] = replace_env_variables(value)
        elif isinstance(item, list):
            return [replace_env_variables(elem) for elem in item]
        elif isinstance(item, str):
            return env_var_pattern.sub(lambda match: os.environ.get(match.group(1), match.group(0)), item)
        return item

    config = replace_env_variables(config)

    with open('./config/config-resolved.yaml', 'w') as file:
        yaml.dump(config, file)

    return config
