"""
This module contains all functions that handle requests on the REST api.
"""
import logging
import os

from django.http import HttpResponseForbidden
from django.http.request import QueryDict
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from channels import Group
from utils import Status, Command
import utils.path as up

from server.utils import StatusResponse
from django.db.models import Q

from .models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    Script as ScriptModel,
    Filesystem as FilesystemModel,
    ScriptGraphFiles as SGFModel,
    ScriptGraphPrograms as SGPModel,
)

from .scripts import Script
from .forms import SlaveForm, ProgramForm, FilesystemForm
from .consumers import notify

from .errors import FilesystemError, FsimError
from .controller import (
    prog_start,
    prog_stop,
    fs_delete,
    fs_move,
    fs_restore,
    slave_wake_on_lan,
)

LOGGER = logging.getLogger("fsim.api")


def add_slave(request):
    """
    Process POST requests which adds new SlaveModel and GET requests to query
    for SlaveModel which contains the query string.

    Parameters
    ----------
        request: HttpRequest

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'POST':
        form = SlaveForm(request.POST)
        if form.is_valid():
            form.save()
            return StatusResponse(Status.ok(""))
        return StatusResponse(Status.err(form.errors))
    elif request.method == 'GET':
        # the URL takes an argument with ?q=<string>
        # e.g. /slaves?q=test
        query = request.GET.get('q', '')
        return StatusResponse.ok(
            list(
                set([
                    obj['name']
                    for obj in SlaveModel.objects.filter(
                        name__contains=query).values("name")
                ])))
    else:
        return HttpResponseForbidden()


def manage_slave(request, slave_id):
    """
    Process DELETE, PUT and POST requests for the SlaveModel ressource.

    Parameters
    ----------
        request: HttpRequest
        id: Unique identifier of a slave

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'DELETE':
        # i can't find any exceptions that can be thrown in our case
        try:
            SlaveModel.objects.get(id=slave_id).delete()
            return StatusResponse.ok("")
        except SlaveModel.DoesNotExist as err:
            return StatusResponse.err(str(err))

    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        try:
            model = SlaveModel.objects.get(id=slave_id)
            form = SlaveForm(QueryDict(request.body), instance=model)

            if form.is_valid():
                form.save()
                return StatusResponse.ok("")
            else:
                return StatusResponse.err("")
        except SlaveModel.DoesNotExist as err:
            return StatusResponse.err(str(err))
    else:
        return HttpResponseForbidden()


def shutdown_slave(request, slave_id):
    """
    Process GET requests which will shutdown a slave.

    Parameters
    ----------
        request: HttpRequest
        id: Unique identifier of a slave

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            slave = SlaveModel.objects.get(id=slave_id)
            if slave.is_online:
                Group('client_' + str(slave_id)).send({
                    'text':
                    Command(method="shutdown").to_json()
                })
                notify({
                    "message":
                    "Send shutdown Command to {}".format(slave.name)
                })
                return StatusResponse(Status.ok(''))
            else:
                return StatusResponse(
                    Status.err('Can not shutdown offline Client'))
        except SlaveModel.DoesNotExist as err:
            return StatusResponse.err(str(err))
    else:
        return HttpResponseForbidden()


def wol_slave(request, slave_id):
    """
    Process GET requests which will start a Slave via Wake-On-Lan.

    Parameters
    ----------
        request: HttpRequest
        id: Unique identifier of a slave

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            slave = SlaveModel.objects.get(id=slave_id)
            slave_wake_on_lan(slave)
            notify({
                "message":
                "Send start command to client `{}`".format(slave.name)
            })
            return StatusResponse.ok("")
        except SlaveModel.DoesNotExist as err:
            return StatusResponse.err(str(err))
    else:
        return HttpResponseForbidden()


def add_program(request):
    """
    Process POST requests which adds new ProgramModel and GET requests to query
    for ProgramModel which contains the query string.

    Parameters
    ----------
        request: HttpRequest

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'POST':
        form = ProgramForm(request.POST or None)

        if form.is_valid():
            program = form.save(commit=False)
            program.slave = form.cleaned_data['slave']
            try:
                program.full_clean()
                form.save()
                return StatusResponse.ok("")
            except ValidationError as _:
                error_dict = {
                    'name':
                    ["Program with this Name already exists on this Client."]
                }
                return StatusResponse.err(error_dict)
        else:
            return StatusResponse.err(form.errors)
    elif request.method == 'GET':
        # the URL takes an argument with ?q=<string>
        # e.g. /programs?q=test
        query = request.GET.get('q', '')
        return StatusResponse(
            Status.ok(
                list(
                    set([
                        obj['name']
                        for obj in ProgramModel.objects.filter(
                            name__contains=query).values("name")
                    ]))))
    else:
        return HttpResponseForbidden()


def manage_program(request, program_id):
    """
    Process DELETE, PUT and POST requests for the ProgramModel ressource.

    Parameters
    ----------
        request: HttpRequest
        slaveId: Unique identifier of a slave
        programId: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'DELETE':
        ProgramModel.objects.filter(id=program_id).delete()
        return StatusResponse.ok("")
    if request.method == 'POST':
        try:
            program = ProgramModel.objects.get(id=program_id)
            if program.enable():
                return StatusResponse.ok("")
            else:
                return StatusResponse.err(
                    'Can not start {} because {} is offline!'.format(
                        program.name, program.slave.name))
        except ProgramModel.DoesNotExist:
            return StatusResponse.err(
                "Can not modify unknown program with id `{}`.".format(
                    program_id))
    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        model = ProgramModel.objects.get(id=program_id)
        form = ProgramForm(QueryDict(request.body), instance=model)
        if form.is_valid():
            program = form.save(commit=False)
            try:
                program.full_clean()
                form.save()
                return StatusResponse.ok("")
            except ValidationError as _:
                error_dict = {
                    'name':
                    ['Program with this Name already exists on this Client.']
                }
                return StatusResponse.err(error_dict)
        else:
            return StatusResponse.err(form.errors)
    else:
        return HttpResponseForbidden()


def stop_program(request, program_id):
    """
    Process GET requests which will stop a running programm on a slave.

    Parameters
    ----------
        request: HttpRequest
        id: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            program = ProgramModel.objects.get(id=program_id)
            try:
                prog_start(program)
                return StatusResponse.ok("")
            except FsimError as err:
                return StatusResponse(err)
        except ProgramModel.DoesNotExist:
            return StatusResponse.err(
                "Can not stop unknown program with id `{}`.".format(
                    program_id))
    else:
        return HttpResponseForbidden()


def add_script(request):
    """
    Process POST requests which adds new SlaveModel.

    Parameters
    ----------
        request: HttpRequest

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'POST':
        try:
            script = Script.from_json(request.body.decode('utf-8'))
            script.save()
            return StatusResponse.ok("")
        except KeyError as err:
            return StatusResponse.err("Could not find required key {}".format(
                err.args[0]))
        except TypeError:
            return StatusResponse.err("Wrong array items.")
        except ValueError as err:
            return StatusResponse.err(str(err))
        except IntegrityError:
            return StatusResponse.err("Script with that name already exists.")
    else:
        return HttpResponseForbidden()


def manage_script(request, script_id):
    """
    Process GET, DELETE requests for the ScriptModel ressource.

    Parameters
    ----------
        request: HttpRequest
        script_id: Unique identifier of script

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            # adds ?slaves=int&program_key=int&filesystem_key=int to the URL
            # to allow a dynamic format for the json string
            slave_key = request.GET.get('slaves', 'int')
            program_key = request.GET.get('programs', 'int')
            filesystem_key = request.GET.get('filesystems', 'int')

            if slave_key != 'str' and slave_key != 'int':
                return StatusResponse(
                    Status.err(
                        "slaves only allow str or int. (given {})".format(
                            slave_key)))

            if program_key != 'str' and program_key != 'int':
                return StatusResponse(
                    Status.err(
                        "programs only allow str or int. (given {})".format(
                            program_key)))

            if filesystem_key != 'str' and filesystem_key != 'int':
                return StatusResponse(
                    Status.err(
                        "filesystems only allow str or int. (given {})".format(
                            filesystem_key)))

            script = Script.from_model(
                script_id,
                slave_key,
                program_key,
                filesystem_key,
            )
            return StatusResponse.ok(dict(script))
        except ScriptModel.DoesNotExist:
            return StatusResponse.err("Script does not exist.")

    elif request.method == 'DELETE':
        ScriptModel.objects.filter(id=script_id).delete()
        return StatusResponse.ok("")
    else:
        return HttpResponseForbidden()


def run_script(request, script_id):
    """
    Process GET requests for the ScriptModel ressource.

    Parameters
    ----------
        request: HttpRequest
        script_id: Unique identifier of script

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """

    if request.method == 'GET':
        try:
            script = ScriptModel.objects.get(id=script_id)
            # only allow the start of a script if the old one is finished
            if FSIM_CURRENT_SCHEDULER.start(script.id):
                FSIM_CURRENT_SCHEDULER.notify()
                return StatusResponse.ok("Started script {}".format(
                    script.name))
            else:
                return StatusResponse.err("A script is still running.")
        except ScriptModel.DoesNotExist:
            return StatusResponse.err(
                "The script with the id {} does not exist.".format(script_id))
    else:
        return HttpResponseForbidden()


def filesystem_set(request):
    """
    Process POST requests which adds new FilesystemModel and GET requests to query
    for FilesystemModel which contains the query string.

    Parameters
    ----------
        request: HttpRequest

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'POST':
        form = FilesystemForm(request.POST or None)

        if form.is_valid():
            filesystem = form.save(commit=False)
            filesystem.slave = form.cleaned_data['slave']

            try:
                filesystem.full_clean()
                # IMPORTANT: remove trailing path seperator (if not the query will not
                # work [the query in filesystem_move])
                filesystem.destination_path = up.remove_trailing_path_seperator(
                    filesystem.destination_path)
                filesystem.source_path = up.remove_trailing_path_seperator(
                    filesystem.source_path)
                form.save()

                return StatusResponse.ok("")
            except ValidationError as err:
                LOGGER.warning(
                    "Error while adding filesystem `%s`: %s",
                    filesystem.name,
                    err,
                )

                string = err.message_dict['__all__'][0]
                if 'Source path' in string and 'Destination path' in string and 'Slave' in string:

                    error_msg = 'Filesystem with this source path and destination path already exists on this Client.'
                    error_dict = {
                        'source_path': [error_msg],
                        'destination_path': [error_msg],
                    }
                elif 'Name' in err.message_dict['__all__'][0] and 'Slave' in err.message_dict['__all__'][0]:
                    error_dict = {
                        'name': [
                            'Filesystem with this Name already exists on this Client.'
                        ]
                    }
                return StatusResponse.err(error_dict)
        else:
            return StatusResponse.err(form.errors)

    elif request.method == 'GET':
        # the URL takes an argument with ?q=<string>
        # e.g. /filesystems?q=test
        query = request.GET.get('q', '')

        return StatusResponse.ok(
            list(
                set([
                    obj['name']
                    for obj in FilesystemModel.objects.filter(
                        name__contains=query).values("name")
                ])))
    else:
        return HttpResponseForbidden()


def filesystem_move(request, filesystem_id):
    """
    Process GET requests for the FilesystemModel(move) ressource.

    Parameters
    ----------
        request: HttpRequest
        fileId: Unique identifier of a filesystem

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            filesystem = FilesystemModel.objects.get(id=filesystem_id)
            try:
                fs_move(filesystem)
                return StatusResponse(Status.ok(""))
            except FilesystemError as err:
                LOGGER.warning(
                    "Error while moving filesystem `%s`: %s",
                    filesystem.name,
                    err,
                )
                return StatusResponse(err)
        except FilesystemModel.DoesNotExist:
            return StatusResponse.err(
                "Can not move unknown filesystem with id `{}`.".format(
                    filesystem_id))
    else:
        return HttpResponseForbidden()


def filesystem_restore(request, filesystem_id):
    """
    Process GET requests for the FilesystemModel(restore) ressource.

    Parameters
    ----------
        request: HttpRequest
        fileId: Unique identifier of a filesystem

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            filesystem = FilesystemModel.objects.get(id=filesystem_id)
            try:
                fs_restore(filesystem)
                return StatusResponse(Status.ok(""))
            except FilesystemError as err:
                LOGGER.warning(
                    "Error while restoring filesystem `%s`: %s",
                    filesystem.name,
                    err,
                )
                return StatusResponse(err)
        except FilesystemModel.DoesNotExist:
            return StatusResponse.err(
                "Can not restore unknown filesystem with id `{}`.".format(
                    filesystem_id))
    else:
        return HttpResponseForbidden()


def filesystem_entry(request, filesystem_id):
    """
    Process DELETE requests for the FilesystemModel ressource.

    Parameters
    ----------
        request: HttpRequest
        fileId: Unique identifier of a filesystem

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than DELETE.
    """

    if request.method == 'DELETE':
        try:
            filesystem = FilesystemModel.objects.get(id=filesystem_id)
            try:
                fs_delete(filesystem)
                return StatusResponse.ok("")
            except FilesystemError as err:
                LOGGER.warning(
                    "Error while deleting filesystem `%s`: %s",
                    filesystem.name,
                    err,
                )
                return StatusResponse(err)
        except FilesystemModel.DoesNotExist:
            return StatusResponse.err(
                "Can not delete unknown filesystem with id `{}`.".format(
                    filesystem_id))
    else:
        return HttpResponseForbidden()
