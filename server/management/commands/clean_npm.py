from django.core.management.base import BaseCommand
import os

class Command(BaseCommand):
    help = 'Removes unused files from node_modules'

    def handle(self, *args, **options):
        html_files = []

        for dirpath, dirnames, filenames in os.walk("."):
            for filename in [f for f in filenames if f.endswith(".html")]:
                filepath = os.path.join(dirpath, filename)
                if 'node_modules' not in filepath:
                    html_files.append(filepath)

        dependencies = []
        for path in html_files:
            with open(path, 'r') as file:
                for line in file:
                    if '{% static' in line:
                        line = line.split("'")[1]
                        if 'node/' in line:
                            line = line.replace('node/','./node_modules/')
                            # save the whole folder
                            line = line.rsplit('/', 1)[0]

                            # if a distfolder exist save it
                            new_line = ''
                            for folder in line.split('/'):
                                new_line += folder
                                dependencies.append(new_line)
                                new_line += '/'

        print(dependencies)

        for dirpath, dirnames, filenames in os.walk("./node_modules"):
            if dirpath not in dependencies:
                for filename in filenames:
                    os.remove(dirpath + '/' + filename)

        deleted = True
        while deleted:
            deleted = False
            for dirpath, dirnames, filenames in os.walk("./node_modules"):
                if not dirnames and not filenames:
                    os.rmdir(dirpath)
                    deleted = True
                    
