from django.views.generic import TemplateView, ListView

from .models import Slave as SlaveModel
from .models import Script as ScriptModel
from .forms import SlaveForm
from .forms import ProgramForm
from .forms import FileForm


class WelcomeView(TemplateView):
    template_name = 'frontend/welcome.html'


class ScriptView(ListView):
    template_name = "frontend/scripts/base.html"
    model = ScriptModel
    context_object_name = "scripts"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['navbar_link'] = "scripts"
        return context


class SlavesView(ListView):
    template_name = "frontend/slaves/base.html"
    model = SlaveModel
    context_object_name = "slaves"

    def get_context_data(self, **kwargs):
        context = super(SlavesView, self).get_context_data(**kwargs)
        context['slave_form'] = SlaveForm()
        context['program_form'] = ProgramForm()
        context['file_form'] = FileForm()
        context['navbar_link'] = "slaves"
        return context
