from django.conf.urls import url

from frontend import views
from frontend import api

app_name = 'frontend'

urlpatterns = [
    url(r'^welcome$', views.WelcomeView.as_view(), name='welcome'),
    url(r'^slaves/$', views.SlavesView.as_view(), name='slaves'),
    url(r'^scripts/$', views.ScriptsView.as_view(), name='scripts'),
    url(r'^script/(?P<pk>[0-9]+)$', views.ScriptView.as_view(), name='script'),
    url(r'^api/slaves', api.add_slave, name='add_slaves'),
    url(r'^api/slave/([0-9]+)$', api.manage_slave, name='manage_slave'),
    url(r'^api/script/([0-9]+)$', api.manage_script, name='manage_script'),
    url(r'^api/programs$', api.add_program, name='add_program'),
    url(r'^api/slave/([0-9]+)/wol$', api.wol_slave, name='wol_slave'),
    url(r'^api/slave/([0-9]+)/shutdown$',
        api.shutdown_slave,
        name='shutdown_slave'),
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
        except AttributeError:
            pass


# Flush status tables DO NOT DELETE!
flush('ProgramStatus', 'SlaveStatus')
