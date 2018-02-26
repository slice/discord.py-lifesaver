# -*- coding: utf-8 -*-
"""
MIT License

Copyright (c) 2017 - 2018 slice

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Any, Dict

from ruamel.yaml import YAML

NO_DEFAULT = object()


class Field:
    def __init__(self, field_type, *, default=NO_DEFAULT, optional: bool = False):
        self.type = field_type
        self.default = default
        self.optional = optional


class ConfigError(Exception):
    """An error thrown by the Config loader."""
    pass


class Config:
    def __init__(self, data, *, loaded_from=None):
        self.loaded_from = loaded_from

        for key in dir(self):
            field = getattr(self, key)

            if not isinstance(field, Field):
                continue

            if key not in data and (not field.optional and field.default is NO_DEFAULT):
                raise ConfigError('Missing required config field: {}'.format(key))

            # If we get here and field.default is NO_DEFAULT, then optional=True was provided but no default value
            # was provided, so just fall back to None.
            value = data.get(key, None if field.default is NO_DEFAULT else field.default)

            if field.type is not Any and not isinstance(value, field.type):
                raise ConfigError('Expected field value of type "{}" for {}, instead got value of type "{}".'.format(
                    type(field.type).__name__, key,
                    type(value).__name__))

            self.__dict__[key] = value

        if not getattr(self, 'strict', False):
            self.__dict__.update(data)

    @classmethod
    def load(cls, file: str):
        """
        Creates a new :class:`Config` and loads a YAML file into it.

        Parameters
        ----------
        file : str
            The filename to load YAML from.

        Returns
        -------
        Config
            The loaded configuration instance.
        """
        with open(file, 'r') as fp:
            yaml = fp.read()
            return cls(YAML(typ='safe').load(yaml), loaded_from=file)

    def to_dict(self) -> Dict[str, Any]:
        """
        Returns
        -------
        dict of str: any
            This configuration as a dict.
        """
        return self.__dict__
