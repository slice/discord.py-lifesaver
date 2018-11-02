# encoding: utf-8

import typing
from collections import UserDict

from ruamel.yaml import YAML

from lifesaver.errors import LifesaverError
from lifesaver.utils import merge_dicts


class ConfigError(LifesaverError):
    """An error thrown by the Config loader."""


class Config(UserDict):
    """A bot or cog configuration."""

    def __init__(self, data, *, loaded_from: str = None):
        super().__init__(data)
        self.loaded_from = loaded_from

        for key, value in data.items():
            try:
                default_value = getattr(self, key)

                if isinstance(default_value, dict) and isinstance(value, dict):
                    # Merge dictionaries instead of overwriting the default value.
                    setattr(self, key, merge_dicts(default_value, value))
                    continue
            except AttributeError:
                # Let custom attributes be set.
                pass

            setattr(self, key, value)

    @classmethod
    def load(cls, path: str) -> 'Config':
        """Creates a Config instance from a file path.

        Parameters
        ----------
        path
            The path to a YAML file.
        """
        with open(path, 'r') as fp:
            yaml = fp.read()
            return cls(YAML().load(yaml), loaded_from=path)

    @property
    def as_dict(self) -> typing.Dict[typing.Any, typing.Any]:
        """Return this Config as a dict."""
        return self.data
