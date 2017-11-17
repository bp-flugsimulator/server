from django.conf.urls import url

from frontend import views
from frontend import api

app_name = 'frontend'

urlpatterns = [
    url(r'^welcome', views.WelcomeView.as_view(), name='welcome'),
    url(r'^slaves/$', views.SlavesView.as_view(), name='slaves'),
    url(r'^api/add_slave', api.add_slave, name='add_slaves')
]
