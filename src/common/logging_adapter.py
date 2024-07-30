"""This module contains class KeyValContextLogger - a custom adapter derived from logging.LoggerAdapter"""

import logging
import sys
from typing import Any, Tuple


class KeyValContextLogger(logging.LoggerAdapter):
    """
    Custom LoggerAdapter to inject context (e.g. correlation id) and to transform log as series of key-value pairs
    """

    def __init__(self, logger, **kwargs):
        super(KeyValContextLogger, self).__init__(logger, extra=kwargs)

    def process(self, message, kwargs) -> Tuple[str, dict[str, Any]]:
        """
        Override logging.LoggerAdapter.process to format the log message as key-values pairs

        :param message: logging message
        :param kwargs: keyword arguments
        :returns: tuple of key-value formatted message and dict of reserved kwargs
        """
        reserved_keys = ["exc_info", "extra", "stack_info"]
        reserved_kwargs = {k: kwargs.pop(k) for k in reserved_keys if k in kwargs}
        log_params = dict(event=message)
        if isinstance(kwargs, dict):
            log_params.update(kwargs)
        log_params.update(self.extra)
        kv_msg = " ".join([f'{k}="{v}"' for (k, v) in log_params.items()])
        return kv_msg, reserved_kwargs

    def error(self, msg, *args, **kwargs) -> None:
        """
        Handle error and exception calls by examining sys.exc_info

        :param msg: error log message
        :param args: additional positional arguments to be delegated to super
        :param kwargs:  keyword arguments to be delegated to super

        """
        exc_info = sys.exc_info()
        if all([var is not None for var in exc_info]):
            _type, _value, _traceback = exc_info
            kwargs["error_type"] = _type.__name__
            kwargs["error_message"] = _value
            super(KeyValContextLogger, self).exception(msg, *args, **kwargs)
        else:
            super(KeyValContextLogger, self).error(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=False, **kwargs):
        """
        Delegates to method error of self

        :param msg: log message
        :param args: additional positional arguments to be delegated
        :param exc_info:  (Default value = False) Ignored
        :param kwargs: keyword arguments to be delegated

        """
        self.error(msg, *args, **kwargs)
