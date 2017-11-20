from django.views.generic import TemplateView, ListView
from django.views.generic.edit import FormMixin


from .models import Slave as SlaveModel
from .forms import SlaveForm

class WelcomeView(TemplateView):
    template_name = 'frontend/welcome.html'

class SlavesView(FormMixin, ListView):
    template_name = "frontend/slaves.html"
    model = SlaveModel
    context_object_name = "slaves"
    form_class = SlaveForm
