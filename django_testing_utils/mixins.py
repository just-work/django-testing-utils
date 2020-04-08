from datetime import timedelta, datetime
from typing import TypeVar, Union, List, Tuple, Any, TYPE_CHECKING, Dict, cast
from unittest import mock

from django.db import models
from django.test import TestCase
from django.utils import timezone

second = timedelta(seconds=1)
minute = timedelta(minutes=1)
hour = timedelta(hours=1)
day = timedelta(days=1)

M = TypeVar('M', bound=models.Model)

# type definition for TestCase subclass mixed with TimeMixin
TimeDerived = Union["TimeMixin", TestCase]


class MockedDateTime(datetime):
    """
    Stub for DateTimeField auto_now/auto_now_add.

    Helps to override model_utils.TimeStampedModel.created.default
    """

    @classmethod
    def utcnow(cls):  # type: ignore
        # noinspection PyUnresolvedReferences
        return timezone.utc.normalize(timezone.now())


if TYPE_CHECKING:  # pragma: no cover
    TimeMixinTarget = TestCase
else:
    TimeMixinTarget = object


class TimeMixin(TimeMixinTarget):
    """ Mixin to freeze time in django tests."""
    now: datetime

    def setUp(self) -> None:
        super().setUp()
        self.now = timezone.now()
        self.now_patcher = mock.patch('django.utils.timezone.now',
                                      side_effect=self.get_now)
        self.now_patcher.start()

        self.timezone_datetime_patcher = mock.patch(
            'django.utils.timezone.datetime',
            new_callable=mock.PropertyMock(return_value=MockedDateTime))
        self.timezone_datetime_patcher.start()

    def tearDown(self) -> None:
        super().tearDown()
        self.timezone_datetime_patcher.stop()
        self.now_patcher.stop()

    def get_now(self) -> datetime:
        return self.now


class BaseTestCaseMeta(type):
    """
    Metaclass for `BaseTestCases` to override `cls.__setattr__`.

    It is useful to create django models in `TestCase` class methods, like
    `setUpTestData` or `setUpClass`. Main advantage of such implementation is
    that every object is created once per test case, not once per test. Main
    disadvantage is that every object preserves in-memory state between
    subsequent tests.

    This metaclass intercepts adding new django model instances as cls members
    and collect it to created_objects list. This list is then used to reset
    in-memory state by calling `refresh_from_db` in `setUp()`.


    """
    _created_objects: List[Tuple[int, models.Model]]

    def __new__(mcs, name: str, bases: Tuple[type, ...],
                attrs: Dict[str, Any]) -> 'BaseTestCaseMeta':
        # Add created django model instances cache as class attribute
        attrs['_created_objects'] = []
        instance = super().__new__(mcs, name, bases, attrs)
        return cast("BaseTestCaseMeta", instance)

    def __setattr__(cls, key: str, value: Any) -> None:
        if isinstance(value, models.Model):
            cls._created_objects.append((value.pk, value))
        return super().__setattr__(key, value)


class BaseTestCase(TimeMixin, TestCase, metaclass=BaseTestCaseMeta):
    """ Base class for django tests."""

    @classmethod
    def refresh_objects(cls) -> None:
        """
        Reset in-memory changed for django models that are stored as
        class attributes.
        """
        for pk, obj in cls._created_objects:
            obj.pk = pk
            obj.refresh_from_db()
            obj._state.fields_cache.clear()  # type: ignore

    @classmethod
    def forget_object(cls, obj: models.Model) -> None:
        """
        Method for removing django model instance from created objects cache
        """
        cls._created_objects.remove((obj.pk, obj))

    @staticmethod
    def update_object(obj: models.Model, *args: Any, **kwargs: Any) -> None:
        """ Update django model object in database only."""
        args_iter = iter(args)
        kwargs.update(dict(zip(args_iter, args_iter)))
        obj._meta.model.objects.filter(pk=obj.pk).update(**kwargs)

    @staticmethod
    def reload(obj: M) -> M:
        """ Fetch same object from database."""
        return obj._meta.model.objects.get(pk=obj.pk)

    def setUp(self) -> None:
        self.refresh_objects()
        super().setUp()

    def assert_object_fields(self, obj: models.Model, **kwargs: Any) -> None:
        """ Obtains an object from database and compares field values."""
        if obj.pk:
            obj = self.reload(obj)
        for k, v in kwargs.items():
            value = getattr(obj, k)
            self.assertEqual(value, v)
