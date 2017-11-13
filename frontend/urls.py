from django.conf.urls import url

from frontend import views

app_name = 'frontend'

urlpatterns = [
    url(r'^welcome', views.WelcomeView.as_view(), name='welcome'),
]
