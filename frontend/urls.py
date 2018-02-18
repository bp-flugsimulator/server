"""
This module specifies which function handles which url.
In addition the module contains oneshot operations that are executed
on server start
"""

from django.conf.urls import url
from frontend import views, api
# from frontend import init_database

app_name = 'frontend'  # pylint: disable=C0103

urlpatterns = [  # pylint: disable=C0103
    url(r'^welcome$', views.WelcomeView.as_view(), name='welcome'),
    url(r'^slaves/$', views.SlavesView.as_view(), name='slaves'),
    url(r'^scripts/$', views.ScriptsView.as_view(), name='scripts'),
    url(r'^scripts/run$', views.RunScriptView.as_view(), name='scripts_run'),
    url(r'^downloads/$', views.DownloadView.as_view(), name='downloads'),
    url(r'^api/scripts$', api.add_script, name='add_script'),
    url(r'^api/script/([0-9]+)$', api.manage_script, name='manage_script'),
    url(r'^api/script/([0-9]+)/run$', api.run_script, name='run_script'),
    url(r'^api/slaves', api.add_slave, name='add_slaves'),
    url(r'^api/slave/([0-9]+)$', api.manage_slave, name='manage_slave'),
    url(r'^api/slave/([0-9]+)/wol$', api.wol_slave, name='wol_slave'),
    url(r'^api/slave/([0-9]+)/shutdown$',
        api.shutdown_slave,
        name='shutdown_slave'),
    url(r'^api/programs$', api.add_program, name='add_program'),
    url(r'^api/program/([0-9]+)$', api.manage_program, name='manage_program'),
    url(r'^api/program/([0-9]+)/stop$', api.stop_program, name='stop_program'),
    url(r'^api/program/([0-9]+)/log$',api.program_manage_log,name='program_manage_log'),
    url(r'^api/program/([0-9]+)/log/enable$',api.program_enable_logging,name='program_enable_logging'),
    url(r'^api/program/([0-9]+)/log/disable$',api.program_disable_logging,name='program_disable_logging'),
    url(r'^api/files$', api.add_file, name='add_file'),
    url(r'^api/file/([0-9]+)$', api.manage_file, name='manage_file'),
]
