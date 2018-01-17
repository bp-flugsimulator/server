"""
This module contains all views of the frontend application
"""

from django.views.generic import TemplateView, ListView

from .models import Slave as SlaveModel
from .models import Script as ScriptModel
from .forms import SlaveForm
from .forms import ProgramForm
from .forms import FileForm
from .forms import RunScriptForm


class WelcomeView(TemplateView):
    """
    generates view for /welcome
    """
    template_name = 'frontend/welcome.html'


class RunScriptView(ListView):
    """
    generates view for /scripts/run
    """
    template_name = "frontend/scripts/run.html"
    model = ScriptModel
    context_object_name = "scripts"

    def get_context_data(self, **kwargs):  # pylint: disable=w0221
        context = super().get_context_data(**kwargs)
        context['navbar_link'] = "scripts_run"
        context['run_script_form'] = RunScriptForm()
        return context


class ScriptsView(ListView):
    """
    generates view for /scripts
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
    generates view for /slaves
    """
    template_name = "frontend/slaves/base.html"
    model = SlaveModel
    context_object_name = "slaves"

    def get_context_data(self, **kwargs):  # pylint: disable=w0221
        context = super(SlavesView, self).get_context_data(**kwargs)
        context['slave_form'] = SlaveForm()
        context['program_form'] = ProgramForm()
        context['file_form'] = FileForm()
        context['navbar_link'] = "slaves"
        return context
