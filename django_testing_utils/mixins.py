from copy import deepcopy
from datetime import timedelta, datetime
from functools import wraps
from typing import TypeVar, Union, Tuple, Any, TYPE_CHECKING, Dict, cast, Type
from unittest import mock

from django.db import models
from django.test import TestCase
from django.utils import timezone

SET_UP_TEST_DATA = 'setUpTestData'
CREATED_OBJECTS = '_created_objects'
RECORDS_OBJECTS = '_records_objects'

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


def wrap_test_data(set_up_test_data: classmethod) -> classmethod:
    """
    This set_up_test_data backports Django-3.2 strategy of resetting state of objects
    created in setUpTestData class set_up_test_data between tests.

    It computes diff of TestCase class __dict__ before and after set_up_test_data call
    and creates a deep copy of objects added in setUpTestData.
    This copy is used to reset class attributes between tests.
    """
    func = set_up_test_data.__func__

    @wraps(func)
    def wrapper(cls: Type[TestCase]) -> None:
        cache = getattr(cls, CREATED_OBJECTS)
        before = cls.__dict__.copy()
        func(cls)
        after = cls.__dict__
        for k, v in after.items():
            if before.get(k) != v:
                # attribute <k> was added or changed in setUpTestData, saving
                cache[k] = v

    return classmethod(wrapper)


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
    in-memory state from deep copy in `setUp()`.
    """
    _created_objects: Dict[str, Any]

    def __new__(mcs, name: str, bases: Tuple[type, ...],
                attrs: Dict[str, Any]) -> 'BaseTestCaseMeta':
        # Add created django model instances cache as class attribute
        attrs[CREATED_OBJECTS] = {}
        setup = attrs.get(SET_UP_TEST_DATA)
        if setup is None:
            # if current class does not define setUpTestData class method, we'll
            # take first one from base classes.
            for base in bases:
                try:
                    setup = getattr(base, SET_UP_TEST_DATA)
                except AttributeError:
                    continue
                else:
                    break
        if setup is not None:
            # do not wrap same method more than once
            if not hasattr(setup, RECORDS_OBJECTS):
                setup = wrap_test_data(setup)
                setattr(setup, RECORDS_OBJECTS, True)
                attrs[SET_UP_TEST_DATA] = setup
        instance = super().__new__(mcs, name, bases, attrs)
        return cast("BaseTestCaseMeta", instance)


class BaseTestCase(TimeMixin, TestCase, metaclass=BaseTestCaseMeta):
    """ Base class for django tests."""

    @staticmethod
    def clone_object(obj: M, **kwargs: Any) -> M:
        """ Clones a django model instance."""
        obj = deepcopy(obj)
        obj.pk = None
        for k, v in kwargs.items():
            setattr(obj, k, v)
        obj.save(force_insert=True)
        return obj

    @classmethod
    def refresh_objects(cls) -> None:
        """
        Reset in-memory changed for django models that are stored as
        class attributes.
        """
        cache = getattr(cls, CREATED_OBJECTS)
        for k, v in cache.items():
            setattr(cls, k, deepcopy(v))

    @classmethod
    def forget_object(cls, obj: models.Model) -> None:
        """
        Method for removing django model instance from created objects cache
        """
        key = None
        for k, v in cls._created_objects.items():
            if type(v) is type(obj) and v.pk == obj.pk:
                key = k
                break
        if key is not None:
            del cls._created_objects[key]

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
            self.assertEqual(value, v, k)
