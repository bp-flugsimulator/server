from django.shortcuts import render
from django.views.generic import TemplateView, ListView

from .models import Slave as SlaveModel


class WelcomeView(TemplateView):
    template_name = 'frontend/welcome.html'


class SlavesView(ListView):
    template_name = 'frontend/slaves.html'
    model = SlaveModel
    context_object_name = 'slaves'
