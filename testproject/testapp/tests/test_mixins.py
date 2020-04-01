from django_testing_utils import mixins
from testapp import models


class BaseTestCaseMetaTestCase(mixins.BaseTestCase):
    """ Tests for base test case metaclass."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = models.Project.objects.create(name='project')
        cls.project2 = models.Project.objects.create(name='project2')
        cls.forget_object(cls.project2)
        cls.project2.delete()

    def test_1_first(self):
        """ Modify something in memory."""
        self.project.name = 'modified'
        self.project.save()

        self.project2.name = 'modified2'

    def test_2_second(self):
        """ class attributes are reset correctly."""
        # This test fill pass only if running whole test case
        self.assertEqual(self.project.name, "project")
        # forgotten object is in modified state
        self.assertEqual(self.project2.name, "modified2")
