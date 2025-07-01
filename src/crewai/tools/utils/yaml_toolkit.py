import pathlib
from ruamel.yaml import YAML

def get_yaml_instance() -> YAML:
    """Returns a configured YAML instance for round-trip operations."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml

def read_yaml(path: pathlib.Path) -> dict:
    """Reads a YAML file and returns its content as a Python dict."""
    yaml = YAML(typ='safe')
    return yaml.load(path)

def write_yaml(data: dict, path: pathlib.Path):
    """Writes a Python dict to a YAML file."""
    yaml = YAML()
    with open(path, 'w') as f:
        yaml.dump(data, f)

def read_yaml_rt(path: pathlib.Path):
    """
    Reads a YAML file using the round-trip loader to preserve
    comments, formatting, etc.
    """
    yaml = get_yaml_instance()
    return yaml.load(path)

def write_yaml_rt(data, path: pathlib.Path):
    """
    Writes data to a YAML file using the round-trip dumper to
    preserve comments, formatting, etc.
    """
    yaml = get_yaml_instance()
    with open(path, 'w') as f:
        yaml.dump(data, f)
