from django.conf.urls import url

from frontend import views
from frontend import api

app_name = 'frontend'

urlpatterns = [
    url(r'^welcome$', views.WelcomeView.as_view(), name='welcome'),
    url(r'^slaves/$', views.SlavesView.as_view(), name='slaves'),
    url(r'^api/slaves', api.add_slave, name='add_slaves'),
    url(r'^api/slave/([0-9]+)$', api.manage_slave, name='manage_slave'),
    url(r'^api/programs$', api.add_program, name='add_program'),
    url(r'^api/slave/([0-9]+)/wol$', api.wol_slave, name='wol_slave'),
    url(r'^api/program/([0-9]+)$', api.manage_program, name='manage_program'),
    url(r'^api/files$', api.add_file, name='add_file'),
]


def flush(*tables):
    """
    Deletes all entries in the given tables.

    Arguments
    ---------
        tables: List of table names (as string)

    """
    from frontend import models

    for table in tables:
        try:
            getattr(models, table).objects.all().delete()
        except:
            pass


# Flush status tables DO NOT DELETE!
flush("SlaveStatus", "ProgramStatus")
