"""
This module contains the 'deploy' command
"""

from django.core.management.base import BaseCommand
from shutil import rmtree, make_archive, copytree
from os import getcwd, mkdir, pardir, remove, walk
from os.path import join, exists, isdir
from subprocess import call

import sass


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
    ]

    def handle(self, *args, **options):
        # copy folder
        self.stdout.write('copy folder')
        copytree(getcwd(), self.DEPLOY_FOLDER)

        # update npm
        if isdir(join(self.DEPLOY_FOLDER, 'node_modules')):
            self.stdout.write('delete node_modules')
            rmtree(join(self.DEPLOY_FOLDER, 'node_modules'))

        call(['npm', 'install'], cwd=self.DEPLOY_FOLDER)

        # compile sass
        self.stdout.write('compile sass')
        call(
            ['python', 'manage.py', 'compilesass'],
            cwd=self.DEPLOY_FOLDER,
        )

        # update packages
        call(['python', 'install.py', '--update'], cwd=self.DEPLOY_FOLDER)

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

        # zip
        print('zip folder')
        make_archive(
            join(getcwd(), pardir, 'server'), 'zip', self.DEPLOY_FOLDER)
