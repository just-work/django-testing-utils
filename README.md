Django-testing-utils
==================

Django-Testing-Utils is a package providing test helpers for django app testing.

![build](https://github.com/just-work/django-testing-utils/workflows/build/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/just-work/django-testing-utils/branch/master/graph/badge.svg)](https://codecov.io/gh/just-work/django-testing-utils)
[![PyPI version](https://badge.fury.io/py/django-testing-utils.svg)](https://badge.fury.io/py/django-testing-utils)

Installation
------------

```shell script
pip install django-testing-utils
```

Usage
-----

## TestCase metaclass

Django 3.2 [introduces](https://docs.djangoproject.com/en/3.2/releases/3.2/#tests)
setUpTestData attributes isolation, but django-testing-utils has slightly 
different way of resetting class attributes between tests. It collects all 
django model objects created in any TestCase class method and runs 
refresh_from_db() when necessary. It also clears fields_cache for such objects.

```python
from django_testing_utils import mixins
from testapp import models

class SomeTestCase(mixins.BaseTestCase):
    """ Some test case that uses django models."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # In large code django docs recommend to create common objects in 
        # this method to speedup tests setup by reusing objects in db.
        cls.project = models.Project.objects.create(name='project')

    def test_something(self):
        # in this test self.project instance is independent from other tests
        ...

```

## Time mocking

There are multiple ways to freeze time in tests:

* ad-hoc mocking with `unittest.mock`
* [freezegun](https://github.com/spulec/freezegun) library
* any system approach that puts working with time in order

django-testing-utils provides a way to use last approach in test with some 
limitations:

* Project code must work with `django.utils.timezone` methods only
* All tests should inherit `TimeMixin` from django-testing-utils

This leads to a systematic way of datetime and timezone usage in the project 
and it's tests.

```python
from django.test import TestCase
from django_testing_utils.mixins import TimeMixin, second


class MyTimeTestCase(TimeMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        # time is not mocked here yet
        ...

    def setUp(self) -> None:
        # not yet...
        super().setUp()
        # ... and here time has been frozen to `self.now`
    
    def test_something(self):
        # simulate time run
        self.now += second
```


## Helpers for django objects

There are some helper methods to work with django objects

* `update_object` - performs an `UPDATE` on django model in a database. This 
  does not affect field values for an object passed to this method.
* `reload` - fetches a new model instance from a database via primary key.
* `assert_object_fields` fetches an actual version from a database and 
  compares all fields with values passed as named arguments
  
```python
from django_testing_utils.mixins import BaseTestCase
from testapp import models

class MyTimeTestCase(BaseTestCase):
    
    def test_something(self):
        obj = models.Project.objects.create()
        # change something in db
        self.update_object(obj, name='new')
        # fetch updated version
        new = self.reload(obj)
        # old object is untouched
        self.assertNotEqual(new.name, obj.name)
        # you could fetch and object and compare some fields in a single call 
        self.assert_object_fields(obj, name='new')
```

## Decorators

* `override_defaults` - a test case/test method decorator to change default 
  values that are stored in `app.defaults` module. The idea of `app.defaults`
  is to reduce a number of rarely changed variables in django settings module by
  moving it to application-specific settings
  
* `disable_patcher` - a context manager / decorator to temporarily disable 
  some `unittest.patch` instances defined in TestCase instance. This breaks 
  open/close principle but allows postponing tests refactoring when some 
  mocks are too generic.  
  
```python
from django.test import TestCase
from django.utils import timezone
from django_testing_utils.mixins import TimeMixin
from django_testing_utils.utils import override_defaults, disable_patchers
from testapp import defaults
import testapp

class MyTestCase(TimeMixin, TestCase):
    
    @override_defaults(testapp.__name__, setting_1=42)
    def test_setting_value(self):
        self.assertEqual(defaults.setting_1, 42)
        
    @disable_patchers('now_patcher')
    def test_real_time(self):
        # now patcher from TimeMixin is now disabled
        with disable_patchers(self.timezone_datetime_patcher):
          # timezone.datetime patcher is not also disabled
          self.assertNotEqual(timezone.now(), timezone.now())

```
