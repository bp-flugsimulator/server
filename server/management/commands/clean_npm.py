from django.core.management.base import BaseCommand
import os


def get_paths(filetype):
    """
    Returns all paths to files with the given filetype

    Parameters
    ----------
    filetype: str
        a filetype ending (example: '.py')
    Returns
    -------
    A list containing strings which specify paths
    to files with the given filetype
    """
    files = []
    for dirpath, _, filenames in os.walk("."):
        for filename in [f for f in filenames if f.endswith(filetype)]:
            filepath = os.path.join(dirpath, filename)
            if 'node_modules' not in filepath:
                files.append(filepath)
    return files


def get_parent_folders(path):
    """
    Returns all paths to parentfolders in
    the given path

    Parameters
    ----------
    path: str
        a path (example '/home/user/git')
    Returns
    -------
    A list containing strings which specify paths
    to the parentfolders in the given path
    """
    new_line = ''
    paths = []
    for folder in path.split('/'):
        new_line += folder
        paths.append(new_line)
        new_line += '/'
    return paths


class Command(BaseCommand):
    help = 'Removes unused files from node_modules'

    def handle(self, *args, **options):
        html_files = get_paths('.html')

        dependencies = []
        # get dependencies from html files
        for path in html_files:
            with open(path, 'r') as file:
                for line in file:
                    if '{% static' in line:
                        line = line.split("'")[1]
                        if 'node/' in line:
                            dependecy_path = line.replace(
                                'node/', './node_modules/').rsplit('/', 1)[0]
                            dependencies.extend(
                                get_parent_folders(dependecy_path))

        """
        # get dependencies from scss files
        scss_files = get_paths('.scss')
        for path in scss_files:
            with open(path, 'r') as file:
                for line in file:
                    if '@import ' in line:
                        dependencies.extend(
                            get_parent_folders('./' + line.split('"')[1]))
        """


        # delete all files that are not a dependency
        for dirpath, dirnames, filenames in os.walk("./node_modules"):
            if dirpath not in dependencies:
                for filename in filenames:
                    os.remove(dirpath + '/' + filename)

        # delete all empty folders
        deleted = True
        while deleted:
            deleted = False
            for dirpath, dirnames, filenames in os.walk("./node_modules"):
                if not dirnames and not filenames:
                    os.rmdir(dirpath)
                    deleted = True
                    
