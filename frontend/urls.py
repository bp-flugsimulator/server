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
    url(r'^api/script/([0-9]+)/copy$', api.copy_script, name='copy_script'),
    url(r'^api/slaves', api.slave_set, name='slave_set'),
    url(r'^api/slave/([0-9]+)$', api.slave_entry, name='slave_entry'),
    url(r'^api/slave/([0-9]+)/wol$', api.slave_wol, name='slave_wol'),
    url(r'^api/slave/([0-9]+)/shutdown$',
        api.slave_shutdown,
        name='slave_shutdown'),
    url(r'^api/programs$', api.program_set, name='program_set'),
    url(r'^api/program/([0-9]+)$', api.program_entry, name='program_entry'),
    url(r'^api/program/([0-9]+)/start$', api.program_start, name='program_start'),
    url(r'^api/program/([0-9]+)/stop$', api.program_stop, name='program_stop'),
    url(r'^api/program/([0-9]+)/log$', api.log_entry, name='log_entry'),
    url(r'^api/program/([0-9]+)/log/enable$', api.log_enable, name='log_enable'),
    url(r'^api/program/([0-9]+)/log/disable$', api.log_disable, name='log_disable'),
    url(r'^api/filesystems$', api.filesystem_set, name='filesystem_set'),
    url(r'^api/filesystem/([0-9]+)$',
        api.filesystem_entry,
        name='filesystem_entry'),
    url(r'^api/filesystem/([0-9]+)/move$',
        api.filesystem_move,
        name='filesystem_move'),
    url(r'^api/filesystem/([0-9]+)/restore$',
        api.filesystem_restore,
        name='filesystem_restore'),
]
