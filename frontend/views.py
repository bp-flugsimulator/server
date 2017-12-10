from django.views.generic import TemplateView, ListView

from .models import Slave as SlaveModel
from .forms import SlaveForm
from .forms import ProgramForm

class WelcomeView(TemplateView):
    template_name = 'frontend/welcome.html'

class SlavesView(ListView):
    template_name = "frontend/slaves.html"
    model = SlaveModel
    context_object_name = "slaves"

    def get_context_data(self, **kwargs):
        context = super(SlavesView, self).get_context_data(**kwargs)
        context['slave_form'] = SlaveForm()
        context['program_form'] = ProgramForm()
        return context
    
