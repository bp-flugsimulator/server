"""
This module specifies which function handles which url.
In addition the module contains oneshot operations that are executed
on server start
"""

from django.conf.urls import url

from frontend import views
from frontend import api

app_name = 'frontend'  # pylint: disable=C0103

urlpatterns = [  # pylint: disable=C0103
    url(r'^welcome$', views.WelcomeView.as_view(), name='welcome'),
    url(r'^slaves/$', views.SlavesView.as_view(), name='slaves'),
    url(r'^scripts/$', views.ScriptsView.as_view(), name='scripts'),
    url(r'^downloads/$', views.DownloadView.as_view(), name='downloads'),
    url(r'^api/scripts$', api.add_script, name='add_script'),
    url(r'^api/script/([0-9]+)$', api.manage_script, name='manage_script'),
    url(r'^api/slaves', api.add_slave, name='add_slaves'),
    url(r'^api/slave/([0-9]+)$', api.manage_slave, name='manage_slave'),
    url(r'^api/slave/([0-9]+)/wol$', api.wol_slave, name='wol_slave'),
    url(r'^api/slave/([0-9]+)/shutdown$',
        api.shutdown_slave,
        name='shutdown_slave'),
    url(r'^api/programs$', api.add_program, name='add_program'),
    url(r'^api/program/([0-9]+)$', api.manage_program, name='manage_program'),
    url(r'^api/program/([0-9]+)/stop$', api.stop_program, name='stop_program'),
    url(r'^api/files$', api.add_file, name='add_file'),
]

# from .models import Slave as SlaveModel, Program as ProgramModel, File as FileModel, Script as ScriptModel

# from .scripts import Script, ScriptEntryProgram, ScriptEntryFile

# slave = SlaveModel(
#     name="test_slave", ip_address="0.0.0.0", mac_address="00:00:00:00:00:00")
# slave.save()

# program = ProgramModel(
#     name="test_program", path="None", arguments="None", slave=slave)
# program.save()

# file = FileModel(
#     name="test_file", sourcePath="None", destinationPath="None", slave=slave)
# file.save()

# script = Script("test_script",
#                 [ScriptEntryProgram(0, "test_program", "test_slave")],
#                 [ScriptEntryFile(0, "test_file", "test_slave")])
# script.save()
