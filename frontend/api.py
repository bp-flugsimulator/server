"""
This module contains all functions that handle requests on the REST api.
"""
import logging
import os

from django.http import HttpResponseForbidden
from django.http.request import QueryDict
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.db.models import Count

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

from .errors import (
    FsimError,
    SlaveNotExistError,
    ProgramNotExistError,
    FilesystemNotExistError,
    SimultaneousQueryError,
    SlaveOfflineError,
    ScriptRunningError,
    ScriptNotExistError,
    QueryTypeError,
)
from .controller import (
    prog_start,
    prog_stop,
    fs_delete,
    fs_move,
    fs_restore,
    prog_log_disable,
    prog_log_enable,
    prog_log_get,
    script_deep_copy,
    slave_wake_on_lan,
)

LOGGER = logging.getLogger("fsim.api")


def script_put_post(data, script_id):
    try:
        script = Script.from_json(data)
        if script_id is None:
            script.save()
        else:
            (new_model, _) = ScriptModel.objects.update_or_create(
                id=script_id,
                defaults={"name": script.name},
            )

            SGFModel.objects.filter(script_id=script_id).delete()
            SGPModel.objects.filter(script_id=script_id).delete()

            for program in script.programs:
                program.save(new_model)
            for filesystem in script.filesystems:
                filesystem.save(new_model)

        return StatusResponse.ok('')
    except FsimError as err:
        return StatusResponse(err)
    except KeyError as err:
        return StatusResponse.err("Could not find required key {}".format(
            err.args[0]))
    except TypeError as err:
        return StatusResponse.err(str(err))
    except ValueError as err:
        return StatusResponse.err(str(err))
    except ValidationError as err:
        return StatusResponse.err('; '.join(err.messages))
    except IntegrityError as err:
        return StatusResponse.err(str(err))


def slave_set(request):
    """
    Process POST requests which adds a new SlaveModel and GET requests to query
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
            return StatusResponse.ok('')
        return StatusResponse.err(form.errors)
    elif request.method == 'GET':
        # the URL takes an argument with ?q=<string>
        # e.g. /slaves?q=test
        query = request.GET.get('q', None)

        programs = request.GET.get('programs', '')
        filesystems = request.GET.get('filesystems', '')

        programs = programs.lower() in ('yes', 'true', '1', 't', 'y')
        filesystems = filesystems.lower() in ('yes', 'true', '1', 't', 'y')

        if query is not None:
            slaves = SlaveModel.objects.filter(
                name__contains=query).values_list(
                    "name",
                    flat=True,
                )
        else:
            if programs and filesystems:
                return StatusResponse(
                    SimultaneousQueryError('filesystems', 'programs'))
            elif programs:
                slaves = SlaveModel.objects.all().annotate(
                    prog_count=Count('program__pk')).filter(
                        prog_count__gt=0).values_list(
                            'name',
                            flat=True,
                        )
            elif filesystems:
                slaves = SlaveModel.objects.all().annotate(
                    filesystem_count=Count('filesystem__pk')).filter(
                        filesystem_count__gt=0).values_list(
                            'name',
                            flat=True,
                        )
            else:
                slaves = SlaveModel.objects.all().values_list(
                    'name',
                    flat=True,
                )

        return StatusResponse.ok(list(slaves))
    else:
        return HttpResponseForbidden()


def slave_entry(request, slave_id):
    """
    Process DELETE, PUT and POST requests for the SlaveModel ressource.

    Parameters
    ----------
        request: HttpRequest
        slave_id: Unique identifier of a slave

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'DELETE':
        # i can't find any exceptions that can be thrown in our case
        SlaveModel.objects.filter(id=slave_id).delete()
        return StatusResponse.ok('')

    elif request.method == 'PUT':
        try:
            # create form from a new QueryDict made from the request body
            # (request.PUT is unsupported) as an update (instance) of the
            # existing slave
            model = SlaveModel.objects.get(id=slave_id)
            form = SlaveForm(QueryDict(request.body), instance=model)

            if form.is_valid():
                form.save()
                return StatusResponse.ok('')
            else:
                return StatusResponse.err(form.errors)
        except SlaveModel.DoesNotExist as err:
            return StatusResponse(SlaveNotExistError(err, slave_id))
    else:
        return HttpResponseForbidden()


def slave_shutdown(request, slave_id):
    """
    Process GET requests which will shutdown a slave.

    Parameters
    ----------
        request: HttpRequest
        slave_id: Unique identifier of a slave

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
                return StatusResponse.ok('')
            else:
                return StatusResponse(
                    SlaveOfflineError('', '', 'shutdown', slave.name))
        except SlaveModel.DoesNotExist as err:
            return StatusResponse(SlaveNotExistError(err, slave_id))

    else:
        return HttpResponseForbidden()


def slave_wol(request, slave_id):
    """
    Process GET requests which will start a Slave via Wake-On-Lan.

    Parameters
    ----------
        request: HttpRequest
        slave_id: Unique identifier of a slave

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

            return StatusResponse.ok('')
        except SlaveModel.DoesNotExist as err:
            return StatusResponse(SlaveNotExistError(err, slave_id))
    else:
        return HttpResponseForbidden()


def program_set(request):
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
                return StatusResponse.ok('')
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
        query = request.GET.get('q', None)
        slave = request.GET.get('slave', None)
        slave_str = request.GET.get('slave_str', False)

        if slave_str:
            slave_str = slave_str.lower() in ('true', 't', 'y', 'yes', '1')

        if query is not None:
            progs = ProgramModel.objects.filter(
                name__contains=query).values_list(
                    "name",
                    flat=True,
                )
        elif slave is not None:

            try:
                if slave_str:
                    slave = SlaveModel.objects.get(name=slave)
                else:
                    try:
                        slave = SlaveModel.objects.get(id=int(slave))
                    except ValueError:
                        return StatusResponse(
                            Status.err("Slave has to be an integer."))  # TODO
            except SlaveModel.DoesNotExist as err:
                return StatusResponse(SlaveNotExistError(err, slave))

            progs = ProgramModel.objects.filter(slave=slave).values_list(
                "name",
                flat=True,
            )

        else:
            progs = ProgramModel.objects.all().values_list(
                "name",
                flat=True,
            )

        return StatusResponse.ok(list(progs))
    else:
        return HttpResponseForbidden()


def program_entry(request, program_id):
    """
    Process DELETE, PUT and POST requests for the ProgramModel ressource.

    Parameters
    ----------
        request: HttpRequest
        program_id: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'DELETE':
        ProgramModel.objects.filter(id=program_id).delete()
        return StatusResponse.ok('')
    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        try:
            model = ProgramModel.objects.get(id=program_id)
            form = ProgramForm(QueryDict(request.body), instance=model)
            if form.is_valid():
                program = form.save(commit=False)
                try:
                    program.full_clean()
                    form.save()
                    return StatusResponse.ok('')
                except ValidationError as _:
                    error_dict = {
                        'name': [
                            'Program with this Name already exists on this Client.'
                        ]
                    }
                    return StatusResponse.err(error_dict)
            else:
                return StatusResponse.err(form.errors)
        except ProgramModel.DoesNotExist as err:
            return StatusResponse(ProgramNotExistError(err, program_id))
    else:
        return HttpResponseForbidden()


def program_start(request, program_id):
    """
    Process GET requests which will start a programm on a slave.

    Parameters
    ----------
        request: HttpRequest
        program_id: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            program = ProgramModel.objects.get(id=program_id)
            prog_start(program)
            return StatusResponse.ok('')
        except FsimError as err:
            return StatusResponse(err)
        except ProgramModel.DoesNotExist as err:
            return StatusResponse(ProgramNotExistError(err, program_id))
    else:
        return HttpResponseForbidden()


def program_stop(request, program_id):
    """
    Process GET requests which will stop a running programm on a slave.

    Parameters
    ----------
        request: HttpRequest
        program_id: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            program = ProgramModel.objects.get(id=program_id)
            try:
                prog_stop(program)
                return StatusResponse.ok('')
            except FsimError as err:
                return StatusResponse(err)
        except ProgramModel.DoesNotExist as err:
            return StatusResponse(ProgramNotExistError(err, program_id))
    else:
        return HttpResponseForbidden()


def log_entry(request, program_id):
    """
    Process GET requests which will request a log from a programm on a slave.

    Parameters
    ----------
        request: HttpRequest
        program_id: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            program = ProgramModel.objects.get(id=program_id)
            prog_log_get(program)
            return StatusResponse.ok('')
        except FsimError as err:
            return StatusResponse(err)
        except ProgramModel.DoesNotExist as err:
            return StatusResponse(ProgramNotExistError(err, program_id))
    else:
        return HttpResponseForbidden()


def log_enable(request, program_id):
    """
    Process GET requests which will enable remote logging on a slave.

    Parameters
    ----------
        request: HttpRequest
        program_id: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            program = ProgramModel.objects.get(id=program_id)
            prog_log_enable(program)
            return StatusResponse.ok('')
        except FsimError as err:
            return StatusResponse(err)
        except ProgramModel.DoesNotExist as err:
            return StatusResponse(ProgramNotExistError(err, program_id))
    else:
        return HttpResponseForbidden()


def log_disable(request, program_id):
    """
    Process GET requests which will disable remote logging on a slave.

    Parameters
    ----------
        request: HttpRequest
        program_id: Unique identifier of a program

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'GET':
        try:
            program = ProgramModel.objects.get(id=program_id)
            prog_log_disable(program)
            return StatusResponse.ok('')
        except FsimError as err:
            return StatusResponse(err)
        except ProgramModel.DoesNotExist as err:
            return StatusResponse(ProgramNotExistError(err, program_id))
    else:
        return HttpResponseForbidden()


def script_set(request):
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
        return script_put_post(request.body.decode('utf-8'), None)
    else:
        return HttpResponseForbidden()


def script_entry(request, script_id):
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

            script = Script.from_model(
                script_id,
                slave_key,
                program_key,
                filesystem_key,
            )
            return StatusResponse.ok(dict(script))
        except ScriptModel.DoesNotExist as err:
            return StatusResponse(ScriptNotExistError(err, script_id))
    elif request.method == 'PUT':
        return script_put_post(request.body.decode('utf-8'), int(script_id))
    elif request.method == 'DELETE':
        ScriptModel.objects.filter(id=script_id).delete()
        return StatusResponse.ok('')
    else:
        return HttpResponseForbidden()


def script_copy(request, script_id):
    """
    Process GET request which constructs a deep copy of a script.

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
            script_deep_copy(script)
            return StatusResponse.ok('')
        except ScriptModel.DoesNotExist as err:
            return StatusResponse(ScriptNotExistError(err, script_id))
    else:
        return HttpResponseForbidden()


def script_run(request, script_id):
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
                return StatusResponse(ScriptRunningError(str(script.name)))
        except ScriptModel.DoesNotExist as err:
            return StatusResponse(ScriptNotExistError(err, script_id))
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
        query = request.GET.get('q', None)
        slave = request.GET.get('slave', None)
        slave_str = request.GET.get('slave_str', False)

        if slave_str:
            slave_str = slave_str.lower() in ('true', 't', 'y', 'yes', '1')

        if query is not None:
            filesystems = FilesystemModel.objects.filter(
                name__contains=query).values_list(
                    "name",
                    flat=True,
                )
        elif slave is not None:
            try:
                if slave_str:
                    slave = SlaveModel.objects.get(name=slave)
                else:
                    try:
                        slave = int(slave)
                    except ValueError as err:
                        return StatusResponse(QueryTypeError(slave, "int"))

                    slave = SlaveModel.objects.get(id=slave)
            except SlaveModel.DoesNotExist as err:
                return StatusResponse(SlaveNotExistError(err, slave))

            filesystems = FilesystemModel.objects.filter(
                slave=slave).values_list(
                    "name",
                    flat=True,
                )
        else:
            filesystems = FilesystemModel.objects.all().values_list(
                "name",
                flat=True,
            )

        return StatusResponse.ok(list(filesystems))
    else:
        return HttpResponseForbidden()


def filesystem_move(request, filesystem_id):
    """
    Process GET requests for the FilesystemModel(move) ressource.

    Parameters
    ----------
        request: HttpRequest
        filesystemId: Unique identifier of a filesystem

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
            except FsimError as err:
                return StatusResponse(err)
        except FilesystemModel.DoesNotExist as err:
            return StatusResponse(FilesystemNotExistError(err, filesystem_id))
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
            except FsimError as err:
                return StatusResponse(err)
        except FilesystemModel.DoesNotExist as err:
            return StatusResponse(FilesystemNotExistError(err, filesystem_id))
    else:
        return HttpResponseForbidden()


def filesystem_entry(request, filesystem_id):
    """
    Process DELETE and PUT requests for the FilesystemModel ressource.

    Parameters
    ----------
        request: HttpRequest
        fileId: Unique identifier of a filesystem

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than DELETE or PUT.
    """

    if request.method == 'DELETE':
        try:
            filesystem = FilesystemModel.objects.get(id=filesystem_id)
            try:
                fs_delete(filesystem)
                return StatusResponse.ok("")
            except FsimError as err:
                return StatusResponse(err)
        except FilesystemModel.DoesNotExist as err:
            return StatusResponse(FilesystemNotExistError(err, filesystem_id))
    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        try:
            model = FilesystemModel.objects.get(id=filesystem_id)

            form = FilesystemForm(QueryDict(request.body), instance=model)
            if form.is_valid():
                filesystem = form.save(commit=False)
                try:
                    filesystem.full_clean()
                    form.save()
                    return StatusResponse.ok('')
                except ValidationError as _:
                    error_dict = {
                        'name': [
                            'Filesystem with this Name already exists on this Client.'
                        ]
                    }
                    return StatusResponse(Status.err(error_dict))
            else:
                return StatusResponse(Status.err(form.errors))
        except FilesystemModel.DoesNotExist as err:
            return StatusResponse(FilesystemNotExistError(err, filesystem_id))
    else:
        return HttpResponseForbidden()
