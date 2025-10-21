
from io import StringIO
from django.core.management import call_command
from django.test import TestCase


class StaticSiteCommandTestSuite(TestCase):

    def test_command_help(self):
        with StringIO() as o:
            call_command('staticsite', 'help', stdout=o)
            o.seek(0)
            command_output = o.read()
            command_lines = command_output.split('\n')
            self.assertEqual(command_lines[0], 'Generates a local static site')

    def test_unknown_command(self):
        with self.assertRaises(SystemExit):
            call_command('staticsite', 'unknown')

    def test_quiet_flag(self):
        with StringIO() as o:
            call_command('staticsite', 'help', '--quiet', stdout=o)
            o.seek(0)
            command_output = o.read()
            self.assertEqual(command_output, '')

    #def test_command_imports_distill_local(self):
    #    import_module('django_distill.management.commands.distill-local')

    #def test_command_imports_distill_publish(self):
    #    import_module('django_distill.management.commands.distill-publish')

    #def test_command_imports_distill_test_publish(self):
    #    import_module('django_distill.management.commands.distill-test-publish')
