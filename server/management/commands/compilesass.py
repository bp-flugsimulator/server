from django.core.management.base import BaseCommand

import sass

class Command(BaseCommand):
    help = 'Compiles the custom sass to css'

    def handle(self, *args, **options):
        sass.compile(dirname=('base/static/scss', 'base/static/css'))
        self.stdout.write('Compiled sass')
