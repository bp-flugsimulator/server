from django.shortcuts import render
from django.views.generic import TemplateView

class WelcomeView(TemplateView):
    template_name = 'frontend/welcome.html'


