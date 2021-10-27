import io

from django.core.files.uploadedfile import SimpleUploadedFile

from django_testing_utils import mixins
from testapp import models


class MixinBaseTestCase(mixins.BaseTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = models.Project.objects.create(name='initial')
        cls.task = models.Task.objects.create(
            name='initial',
            project=cls.project,
            attachment=SimpleUploadedFile(
                name='filename.txt',
                content=io.BytesIO().getvalue()
            ),
            visible=False
        )
        cls.attr = 'a'


class BaseTestCaseMetaTestCase(MixinBaseTestCase):
    """ Tests for base test case metaclass."""

    def test_update_object(self):
        """ update_object updates object in database only"""
        self.update_object(self.project, name='modified')

        self.assertEqual(self.project.name, 'initial')
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'modified')

    def test_clone_object(self):
        """ clones and returns a new object from db"""
        cloned_task = self.clone_object(self.task, name='unique name')

        self.assertNotEqual(self.task.pk, cloned_task.pk)
        self.assertEqual(self.task.project, cloned_task.project)
        self.assertNotEqual(self.task.name, cloned_task.name)
        self.assertEqual(cloned_task.name, 'unique name')
        self.assertEqual(self.task.visible, cloned_task.visible)
        self.assertEqual(self.task.attachment, cloned_task.attachment)

    def test_reload(self):
        """ reload fetches actual object version from db."""
        self.update_object(self.project, name='modified')

        project = self.reload(self.project)
        self.assertEqual(self.project.name, 'initial')
        self.assertEqual(project.name, 'modified')

    def test_assert_object_fields(self):
        """ assert_object_fields reloads object and checks for equality."""
        # collecting assert message
        with self.assertRaises(AssertionError) as ctx:
            self.assertEqual(self.project.name, 'wrong', 'name')

        args = ctx.exception.args

        with self.assertRaises(AssertionError)as ctx:
            self.assert_object_fields(self.project, name='wrong')

        self.assertEqual(ctx.exception.args, args)

        self.assert_object_fields(self.project, name='initial')

    def test_refresh_objects(self):
        """
        refresh_objects updates from db each django model instance created
        in setUpTestData.
        """
        self.project.name = 'changed'
        self.__class__.attr = 'b'

        self.refresh_objects()

        self.assertEqual(self.project.name, 'initial')
        self.assertEqual(self.__class__.attr, 'a')


class ForgetObjectTestCase(MixinBaseTestCase):
    """
    Checks removing saved class attribute from a list
    """

    def test_forget_object(self):
        """
        forget_object removes a django model instance from saved instances
        """
        self.project.name = 'changed'

        self.forget_object(self.project)

        self.refresh_objects()
        # self.project not reset, because it's removed from saved object list
        self.assertEqual(self.project.name, 'changed')


class SetUpTestDataResetTestCase(MixinBaseTestCase):
    """
    Ensures that objects created in setUpTestData are reset between tests
    """

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.project2 = models.Project.objects.create(name='first')

    def test_1_change_something(self):
        """
        First test in testcase that pollutes class attribute
        """
        # change in-memory
        self.project.name = 'changed'
        # change in-db
        self.update_object(self.project2, name='altered')

    def test_2_assert_object_reset(self):
        """
        Second test in testcase that checks that polluted object is reset
        between tests.
        """
        self.assertEqual(self.project.name, 'initial')
        self.assertEqual(self.project2.name, 'first')
