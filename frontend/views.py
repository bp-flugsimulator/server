from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView, FormView, View
from django.views.generic.edit import SingleObjectMixin, FormMixin
from django.core.urlresolvers import reverse


from django.http import HttpResponseForbidden

from .models import Slave as SlaveModel

from django.forms import modelform_factory


class WelcomeView(TemplateView):
    template_name = 'frontend/welcome.html'

class SlavesViewLul(ListView):
    template_name = 'frontend/slaves.html'
    model = SlaveModel
    context_object_name = 'slaves'
    #form = modelform_factory(SlaveModel,fields='__all__')


class SlavesView(FormMixin, ListView):
    template_name = "frontend/slaves.html"
    model = SlaveModel
    context_object_name = "slaves"
    form_class = modelform_factory(SlaveModel,fields='__all__')
