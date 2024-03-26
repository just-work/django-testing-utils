from django.test import SimpleTestCase
from django.utils import timezone

from django_testing_utils.mixins import TimeMixin
from django_testing_utils.utils import override_defaults, disable_patchers
from testproject.testapp import defaults


class OverrideDefaultsTests(SimpleTestCase):
    """ override_defaults test case. """

    def test_original_value(self):
        """ Check the original setting value. """
        self.assertEqual('original1', defaults.setting_1)
        self.assertEqual('original2', defaults.setting_2)

    def test_context_manager_using_module_name(self):
        """ Check the setting value overridden using the module name. """
        self.assertEqual('original1', defaults.setting_1)
        self.assertEqual('original2', defaults.setting_2)

        with override_defaults('testproject.testapp',
                               setting_1='changed1',
                               setting_2='changed2'):
            self.assertEqual('changed1', defaults.setting_1)
            self.assertEqual('changed2', defaults.setting_2)

        self.assertEqual('original1', defaults.setting_1)
        self.assertEqual('original2', defaults.setting_2)

    @override_defaults('testproject.testapp',
                       setting_1='changed1', setting_2='changed2')
    def test_decorator_using_module_name(self):
        """ Check the setting value overridden using the module name. """
        self.assertEqual('changed1', defaults.setting_1)
        self.assertEqual('changed2', defaults.setting_2)


class DisablePatchersTestCase(TimeMixin, SimpleTestCase):
    @disable_patchers('now_patcher', 'timezone_datetime_patcher')
    def test_disable_patcher_for_method(self):
        self.assertNotEqual(timezone.now(), timezone.now())

    def test_disable_patcher_as_context_manager(self):
        self.assertEqual(timezone.now(), timezone.now())
        with disable_patchers(self.now_patcher, self.timezone_datetime_patcher):
            self.assertNotEqual(timezone.now(), timezone.now())
