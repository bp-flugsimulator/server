from django.core.management.base import BaseCommand

import sass

from server.settings import BASE_DIR

class Command(BaseCommand):
    help = 'Compiles the custom sass to css'

    def handle(self, *args, **options):
        sass.compile(dirname=('base/static/base/scss', 'base/static/base/css'))
        self.stdout.write('Compiled sass')
