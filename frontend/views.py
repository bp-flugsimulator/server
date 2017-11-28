from django.views.generic import TemplateView, ListView

from .models import Slave as SlaveModel
from .forms import SlaveForm

class WelcomeView(TemplateView):
    template_name = 'frontend/welcome.html'

class SlavesView(ListView):
    template_name = "frontend/slaves.html"
    model = SlaveModel
    context_object_name = "slaves"
    slave_form = SlaveForm

    def get_context_data(self, **kwargs):
        context = super(SlavesView, self).get_context_data(**kwargs)
        context['slave_form'] = self.slave_form()
        return context
