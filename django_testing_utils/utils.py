from typing import Any, List
from unittest import mock

# noinspection PyProtectedMember
from unittest.mock import _patch

# noinspection PyProtectedMember
from django.test.utils import TestContextDecorator


# noinspection PyPep8Naming
class override_defaults(TestContextDecorator):
    """
    A tool for convenient override default values in config files

    Act as either a decorator or a context manager. If it's a decorator, take a
    function and return a wrapped function. If it's a contextmanager, use it
    with the ``with`` statement. In either event, entering/exiting are called
    before and after, respectively, the function/block is executed.
    """
    enable_exception = None

    def __init__(self, app_name: str, **kwargs: Any):
        """ Save initial parameters.

        :param app_name: the application name
        :param kwargs: default attributes and values to override
        """
        self.app_name = app_name
        self.settings = kwargs
        self.patchers: List[_patch] = []
        super().__init__()

    def enable(self) -> None:
        """ Create patchers, start save and start them. """
        for setting, value in self.settings.items():
            patcher = mock.patch(f'{self.app_name}.defaults.{setting}', value)
            self.patchers.append(patcher)
            patcher.start()

    def disable(self) -> None:
        """ Stop patchers. """
        for patcher in self.patchers:
            patcher.stop()
