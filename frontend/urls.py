from django.conf.urls import url

from frontend import views

app_name = 'frontend'

urlpatterns = [
    url(r'^$', views.HomepageView.as_view(), name='index'),
]
