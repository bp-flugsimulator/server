from django.core.management.base import BaseCommand

import sass

class Command(BaseCommand):
    help = 'Compiles the custom sass to css'

    def handle(self, *args, **options):
        sass.compile(dirname=('base/static/base/scss', 'base/static/base/css'))
        self.stdout.write('Compiled sass')
