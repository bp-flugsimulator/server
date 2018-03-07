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
    # VIEWS
    url(r'^welcome$', views.WelcomeView.as_view(), name='welcome'),
    url(r'^slaves/$', views.SlavesView.as_view(), name='slaves'),
    url(r'^scripts/$', views.ScriptsView.as_view(), name='scripts'),
    url(r'^scripts/run$', views.RunScriptView.as_view(), name='scripts_run'),
    url(r'^downloads/$', views.DownloadView.as_view(), name='downloads'),

    # API
    # Scripts
    url(r'^api/scripts$', api.script_set, name='script_set'),
    url(r'^api/script/([0-9]+)$', api.script_entry, name='script_entry'),
    url(r'^api/script/([0-9]+)/run$', api.script_run, name='script_run'),
    url(r'^api/script/([0-9]+)/copy$', api.script_copy, name='script_copy'),
    # Slaves
    url(r'^api/slaves', api.slave_set, name='slave_set'),
    url(r'^api/slave/([0-9]+)$', api.slave_entry, name='slave_entry'),
    url(r'^api/slave/([0-9]+)/wol$', api.slave_wol, name='slave_wol'),
    url(r'^api/slave/([0-9]+)/shutdown$',
        api.slave_shutdown,
        name='slave_shutdown',),
    # Programs
    url(r'^api/programs$', api.program_set, name='program_set'),
    url(r'^api/program/([0-9]+)$', api.program_entry, name='program_entry'),
    url(r'^api/program/([0-9]+)/start$',
        api.program_start,
        name='program_start',),
    url(r'^api/program/([0-9]+)/stop$', api.program_stop, name='program_stop'),
    url(r'^api/program/([0-9]+)/log$',
        api.program_log_entry, name='program_log_entry'),
    url(r'^api/program/([0-9]+)/log/enable$', api.program_log_enable,
        name='program_log_enable',),
    url(r'^api/program/([0-9]+)/log/disable$', api.program_log_disable,
        name='program_log_disable',),
    # Filesystems
    url(r'^api/filesystems$', api.filesystem_set, name='filesystem_set'),
    url(r'^api/filesystem/([0-9]+)$',
        api.filesystem_entry,
        name='filesystem_entry',),
    url(r'^api/filesystem/([0-9]+)/move$',
        api.filesystem_move,
        name='filesystem_move',),
    url(r'^api/filesystem/([0-9]+)/restore$',
        api.filesystem_restore,
        name='filesystem_restore',),
]
