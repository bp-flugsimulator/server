"""
This module contains all views of the frontend application.
"""

from django.views.generic import TemplateView, ListView

from .models import Slave as SlaveModel
from .models import Script as ScriptModel
from .forms import SlaveForm
from .forms import ProgramForm
from .forms import FilesystemForm

from os import listdir, getcwd, mkdir
from os.path import getsize, join, isdir


class WelcomeView(TemplateView):
    """
    generates view for /welcome
    """
    template_name = 'frontend/welcome.html'


class RunScriptView(TemplateView):
    """
    The site the user will navigate to, if he wants to run a script.
    """
    template_name = "frontend/scripts/run.html"

    def get_context_data(self, **kwargs):  # pylint: disable=w0221
        context = super().get_context_data(**kwargs)
        context['navbar_link'] = "scripts_run"
        context['script'] = ScriptModel.latest()
        context['involved_slaves'] = ScriptModel.get_involved_slaves(
            context['script'])
        context['ran'] = ScriptModel.get_last_ran()
        return context


class ScriptsView(ListView):
    """
    The site the user will navigate to, if he wants add/remove/edit a script.
    """
    template_name = "frontend/scripts/base.html"
    model = ScriptModel
    context_object_name = "scripts"

    def get_context_data(self, **kwargs):  # pylint: disable=w0221
        context = super().get_context_data(**kwargs)
        context['navbar_link'] = "scripts"
        return context


class SlavesView(ListView):
    """
    The site the user will navigate to, if he wants interact with different
    slaves.
    """
    template_name = "frontend/slaves/base.html"
    model = SlaveModel
    context_object_name = "slaves"

    def get_context_data(self, **kwargs):  # pylint: disable=w0221
        context = super(SlavesView, self).get_context_data(**kwargs)
        context['slave_form'] = SlaveForm()
        context['program_form'] = ProgramForm()
        context['file_form'] = FilesystemForm()
        context['navbar_link'] = "slaves"
        return context


class DownloadView(TemplateView):
    """
    The site the user will navigate to, if he wants to download a file.
    """
    template_name = "frontend/downloads/base.html"

    def get_context_data(self, **kwargs):  # pylint: disable=w0221
        context = super(DownloadView, self).get_context_data(**kwargs)

        if not isdir('downloads'):
            mkdir('downloads')

        file_list = []
        for file in listdir('downloads'):
            entry = dict()
            entry['name'] = file
            size = entry['size'] = getsize(join(getcwd(), 'downloads', file))
            if size < pow(2, 10):
                entry['size'] = str(size) + ' B'
            elif size < pow(2, 20):
                entry['size'] = str(round(size / pow(2, 10))) + ' KiB'
            elif size < pow(2, 30):
                entry['size'] = str(round(size / pow(2, 20))) + ' MiB'
            else:
                entry['size'] = str(round(size / pow(2, 30))) + ' GiB'

            file_list.append(entry)

        context['file_list'] = file_list
        context['navbar_link'] = "downloads"
        return context
