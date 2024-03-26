import functools
from typing import Any, List, Union, Callable, Type
from unittest import mock, TestCase
from types import TracebackType
from django.test import utils

# noinspection PyUnresolvedReferences,PyProtectedMember
Patch = mock._patch


# noinspection PyPep8Naming
class override_defaults(utils.TestContextDecorator):
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
        self.patchers: List[Patch] = []
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


# noinspection PyPep8Naming
class disable_patchers:
    """
    Temporarily disables unittest.mock patchers defined in a TestCase instance,
    or passed by value to a decorator/context manager.
    """
    def __init__(self, *patchers: Union[str, Patch]) -> None:
        self.patchers = patchers

    @staticmethod
    def get(obj: Any, name: Union[str, Patch]) -> Patch:
        """ Gets a patcher instance from object by name, or patcher itself.
        """
        if isinstance(name, str):
            return getattr(obj, name)
        return name

    def __call__(self, func: Callable) -> Callable:

        @functools.wraps(func)
        def inner(testcase: TestCase, *args: Any, **kwargs: Any) -> Any:
            try:
                for p in self.patchers:
                    self.get(testcase, p).stop()

                return func(testcase, *args, **kwargs)

            finally:
                for p in self.patchers:
                    self.get(testcase, p).start()

        return inner

    def __enter__(self) -> None:
        for p in self.patchers:
            assert not isinstance(p, str)
            p.stop()

    def __exit__(self,
                 exc_type: Type[Exception],
                 exc_val: Exception,
                 exc_tb: TracebackType) -> None:
        for p in self.patchers:
            assert not isinstance(p, str)
            p.start()
