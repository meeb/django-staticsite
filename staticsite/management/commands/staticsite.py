
import os


from shutil import rmtree

from logging import getLogger
from django.core.management.base import (BaseCommand, CommandError)
from django.conf import settings
#from django_distill.distill import urls_to_distill
#from django_distill.renderer import (run_collectstatic, render_to_dir,
#                                     copy_static_and_media_files, render_redirects)
#from django_distill.errors import DistillError


log = getLogger('main')


class Command(BaseCommand):

    help = 'Generates a local static site'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.quiet = False

    def add_arguments(self, parser):
        parser.add_argument('subcommand', nargs='?', type=str)
        parser.add_argument('--output-directory', dest='output_directory', type=str, default=None)
        parser.add_argument('--target', dest='target', type=str, default='default')
        parser.add_argument('--collectstatic', dest='collectstatic', action='store_true')
        parser.add_argument('--quiet', dest='quiet', action='store_true')
        parser.add_argument('--force', dest='force', action='store_true')
        parser.add_argument('--exclude-staticfiles', dest='exclude_staticfiles', action='store_true')
        parser.add_argument('--generate-redirects', dest='generate_redirects', action='store_true')
        parser.add_argument('--parallel-render', dest='parallel_render', type=int, default=1)

    def write(self, msg):
        if not self.quiet:
            self.stdout.write(msg)

    def handle(self, *args, **options):
        subcommand_map = {
            'help': self.command_help,
            'generate': self.command_generate,
            'publish': self.command_publish,
            'test-target': self.command_test_target,
            'list-static-urls': self.command_list_static_urls,
            'list-publish-targets': self.command_list_publish_targets,

        }
        subcommand_name = options.get('subcommand')
        self.quiet = options.get('quiet')
        if subcommand_name is None:
            subcommand_func = self.command_help
        else:
            subcommand_func = subcommand_map.get(subcommand_name)
        if subcommand_func:
            subcommand_func(*args, **options)
        else:
            raise SystemExit(f'Unknown subcommand specified: {subcommand_name} (try "help")')

    def command_help(self, *args, **options):
        self.write(self.help)
        self.write('')
        self.write('This help message:')
        self.write('    ./manage.py staticsite help')
        self.write('')
        self.write('Generate a local static site:')
        self.write('    ./manage.py staticsite generate --output-directory=<directory_name>')
        self.write('')
        self.write('Generate a static site and publish it to remote object storage backend:')
        self.write('    ./manage.py staticsite publish --target=<target_name>')
        self.write('')
        self.write('Test a publish target is configured correctly:')
        self.write('    ./manage.py staticsite test-target --target=<target_name>')
        self.write('')
        self.write('List all URL routes in the project that have been defined as static:')
        self.write('    ./manage.py staticsite list-static-urls')
        self.write('')
        self.write('List all defined publish targets:')
        self.write('    ./manage.py staticsite list-publish-targets')
        self.write('')
        self.write('Additional options:')
        self.write('')
        self.write('    --collectstatic - when generating a local static site, also run "collectstatic"')
        self.write('    --quiet - no log output')
        self.write('    --force - automatically answer "yes" to all questions')
        self.write('    --exclude-staticfiles - when generating a local static site, exclude static files')
        self.write('    --generate-redirects - create static HTML redirect pages for any 301 or 303 redirects')
        self.write('    --parallel-render=N - number of parallel processes to use when rendering the site, defaults to 1')
        self.write('')

    def command_generate(self, *args, **options):
        pass

    def command_publish(self, *args, **options):
        pass

    def command_test_target(self, *args, **options):
        pass

    def command_list_static_urls(self, *args, **options):
        pass

    def command_list_publish_targets(self, *args, **options):
        pass

'''
        output_dir = options.get('output_dir')
        collectstatic = options.get('collectstatic')
        quiet = options.get('quiet')
        force = options.get('force')
        exclude_staticfiles = options.get('exclude_staticfiles')
        generate_redirects = options.get('generate_redirects')
        parallel_render = options.get('parallel_render')
        if quiet:
            stdout = self._quiet
        else:
            stdout = self.stdout.write
        if not output_dir:
            output_dir = getattr(settings, 'DISTILL_DIR', None)
            if not output_dir:
                e = 'Usage: ./manage.py distill-local [directory]'
                raise CommandError(e)
        if collectstatic:
            run_collectstatic(stdout)
        if not exclude_staticfiles and not os.path.isdir(settings.STATIC_ROOT):
            e = 'Static source directory does not exist, run collectstatic'
            raise CommandError(e)
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        stdout('')
        stdout('You have requested to create a static version of')
        stdout('this site into the output path directory:')
        stdout('')
        stdout('    Source static path:  {}'.format(settings.STATIC_ROOT))
        stdout('    Distill output path: {}'.format(output_dir))
        stdout('')
        if os.path.isdir(output_dir):
            stdout('Distill output directory exists, clean up?')
            stdout('This will delete and recreate all files in the output dir')
            stdout('')
            if force:
                ans = 'yes'
            else:
                ans = input('Type \'yes\' to continue, or \'no\' to cancel: ')
            if ans.lower() == 'yes':
                stdout('Recreating output directory...')
                rmtree(output_dir)
                os.makedirs(output_dir)
            else:
                raise CommandError('Distilling site cancelled.')
        else:
            if force:
                ans = 'yes'
            else:
                ans = input('Does not exist, create it? (YES/no): ')
            if ans.lower() == 'yes':
                stdout('Creating directory...')
                os.makedirs(output_dir)
            else:
                raise CommandError('Aborting...')
        stdout('')
        stdout('Generating static site into directory: {}'.format(output_dir))
        try:
            render_to_dir(output_dir, urls_to_distill, stdout, parallel_render=parallel_render)
            if not exclude_staticfiles:
                copy_static_and_media_files(output_dir, stdout)
        except DistillError as err:
            raise CommandError(str(err)) from err
        stdout('')
        if generate_redirects:
            stdout('Generating redirects')
            render_redirects(output_dir, stdout)
            stdout('')
        stdout('Site generation complete.')
'''
