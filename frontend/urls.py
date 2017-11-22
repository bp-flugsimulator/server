from django.conf.urls import url

from frontend import views
from frontend import api

app_name = 'frontend'

urlpatterns = [
    url(r'^welcome$', views.WelcomeView.as_view(), name='welcome'),
    url(r'^slaves/$', views.SlavesView.as_view(), name='slaves'),
    url(r'^api/slaves', api.add_slave, name='add_slaves'),
    url(r'^api/slave/([0-9]+)', api.manage_slave, name='manage_slave'),
]
