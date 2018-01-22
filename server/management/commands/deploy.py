"""
This module contains the 'deploy' command
"""

from subprocess import call

from os import getcwd, pardir, remove, walk, listdir
from os.path import join, isdir, isfile

from shutil import rmtree, make_archive, copytree

from django.core.management.base import BaseCommand
from django.core.management import utils


class Command(BaseCommand):
    """
    generates the 'compilesass' command
    """
    help = 'generates a zip file that can be deployed'

    DEPLOY_FOLDER = join(getcwd(), pardir, 'server_release')
    IGNORE_LIST = [
        'appveyor.yml',
        'Dockerfile',
        'Jenkinsfile',
        'bp-client.dockerfile',
    ]

    def handle(self, *args, **options):
        # copy folder
        self.stdout.write('copy folder')
        copytree(getcwd(), self.DEPLOY_FOLDER)

        # modify settings
        lines = list()
        with open(join(self.DEPLOY_FOLDER, 'server', 'settings.py'),
                  'r') as settings:
            for line in settings:
                if 'DEBUG' in line:
                    line = 'DEBUG = False\n'
                    self.stdout.write('disabled debug mode')
                if 'SECRET_KEY' in line:
                    line = "SECRET_KEY = '"
                    line += utils.get_random_secret_key() + "'\n"
                    self.stdout.write('generated secret key')
                lines.append(line)

        with open(join(self.DEPLOY_FOLDER, 'server', 'settings.py'),
                  'w') as settings:
            for line in lines:
                settings.write(line)

        # update npm
        if isdir(join(self.DEPLOY_FOLDER, 'node_modules')):
            self.stdout.write('delete node_modules')
            rmtree(join(self.DEPLOY_FOLDER, 'node_modules'))

        call(['npm', 'install'], cwd=self.DEPLOY_FOLDER)

        # compile sass
        call(
            [
                'python',
                'manage.py',
                'compilesass',
            ],
            cwd=self.DEPLOY_FOLDER,
        )

        # clone client
        call(
            ['git', 'clone', 'https://github.com/bp-flugsimulator/client.git'],
            cwd=join(self.DEPLOY_FOLDER, 'downloads'),
        )

        # update packages
        call(
            ['python', 'install.py', '--update'],
            cwd=self.DEPLOY_FOLDER,
        )
        call(
            ['python', 'install.py', '--update'],
            cwd=join(self.DEPLOY_FOLDER, 'downloads'),
        )

        # delete unused files
        for path, dir_names, file_names in walk(self.DEPLOY_FOLDER):
            for directory in dir_names:
                if ((len(directory) > 3) and
                    (directory[0] is '.')) or (directory in self.IGNORE_LIST):
                    rmtree(join(path, directory))
                    self.stdout.write('removed ' + join(path, directory))

            for file in file_names:
                if ((len(file) > 3) and
                    (file[0] is '.')) or (file in self.IGNORE_LIST):
                    remove(join(path, file))
                    self.stdout.write('removed ' + join(path, file))

        # zip client and delete folder
        print('zip client')
        make_archive(
            join(self.DEPLOY_FOLDER, 'downloads', 'client'),
            'zip',
            join(self.DEPLOY_FOLDER, 'downloads', 'client'),
        )
        self.stdout.write('delete client folder')
        rmtree(join(self.DEPLOY_FOLDER, 'downloads', 'client'))

        # collect static files
        self.stdout.write('collect static files')
        call(
            ['python', 'manage.py', 'collectstatic', '--noinput'],
            cwd=self.DEPLOY_FOLDER,
        )

        # set up database
        if isfile(join(self.DEPLOY_FOLDER, 'db.sqlite3')):
            remove(join(self.DEPLOY_FOLDER, 'db.sqlite3'))
            self.stdout.write('deleted database')

        for file in listdir(
                join(self.DEPLOY_FOLDER, 'frontend', 'migrations')):
            if isfile(
                    join(
                        self.DEPLOY_FOLDER,
                        'frontend',
                        'migrations',
                        file,
                    )) and not ('0001_initial.py' in file
                                or '__init__.py' in file):
                remove(
                    join(
                        self.DEPLOY_FOLDER,
                        'frontend',
                        'migrations',
                        file,
                    ))
                self.stdout.write('remove ' + join(
                    self.DEPLOY_FOLDER,
                    'frontend',
                    'migrations',
                    file,
                ))
        call(
            ['python', 'manage.py', 'makemigrations'],
            cwd=self.DEPLOY_FOLDER,
        )
        call(
            ['python', 'manage.py', 'migrate'],
            cwd=self.DEPLOY_FOLDER,
        )

        # zip
        self.stdout.write('zip server')
        make_archive(
            join(getcwd(), pardir, 'server'),
            'zip',
            self.DEPLOY_FOLDER,
        )
        self.stdout.write('delete deploy folder')
        rmtree(self.DEPLOY_FOLDER)
