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

LOGGER = logging.getLogger("fsim.api")
FILE_BACKUP_ENDING = "_BACK"


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
                    Status.err(
                        "Can not query for filesystems and programs at the same time."
                    ))
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

        return StatusResponse(Status.ok(list(slaves)))
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
        SlaveModel.objects.filter(id=slave_id).delete()
        return StatusResponse(Status.ok(''))

    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        model = SlaveModel.objects.get(id=slave_id)
        form = SlaveForm(QueryDict(request.body), instance=model)

        if form.is_valid():
            form.save()
            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(Status.err(form.errors))
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
        if SlaveModel.objects.filter(id=slave_id).exists():
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
        else:
            return StatusResponse(
                Status.err('Can not shutdown unknown Client'))

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
            SlaveModel.wake_on_lan(slave_id)
        except Exception as err:  # pylint: disable=W0703
            return StatusResponse(Status.err(repr(err)), status=500)

        notify({"message": "Send Wake On Lan Packet"})
        return StatusResponse(Status.ok(''))
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
                return StatusResponse(Status.ok(''))
            except ValidationError as _:
                error_dict = {
                    'name':
                    ["Program with this Name already exists on this Client."]
                }
                return StatusResponse(Status.err(error_dict))
        else:
            return StatusResponse(Status.err(form.errors))
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
                            Status.err("Slave has to be an integer."))
            except SlaveModel.DoesNotExist:
                ret_err = "Could not find slave with"
                if slave_str:
                    ret_err += " name `{}`".format(slave)
                else:
                    ret_err += " id `{}`".format(slave)

                ret_err += "."

                return StatusResponse(Status.err(ret_err))

            progs = ProgramModel.objects.filter(slave=slave).values_list(
                "name",
                flat=True,
            )

        else:
            progs = ProgramModel.objects.all().values_list(
                "name",
                flat=True,
            )

        return StatusResponse(Status.ok(list(progs)))
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
        return StatusResponse(Status.ok(''))
    if request.method == 'POST':
        program = ProgramModel.objects.get(id=program_id)
        if program.enable():
            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(
                Status.err('Can not start {} because {} is offline!'.format(
                    program.name, program.slave.name)))
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
                return StatusResponse(Status.ok(''))
            except ValidationError as _:
                error_dict = {
                    'name':
                    ['Program with this Name already exists on this Client.']
                }
                return StatusResponse(Status.err(error_dict))
        else:
            return StatusResponse(Status.err(form.errors))
    else:
        return HttpResponseForbidden()


def stop_program(request, program_id):
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
        if ProgramModel.objects.filter(id=program_id).exists():
            program = ProgramModel.objects.get(id=program_id)
            if program.disable():
                return StatusResponse(Status.ok(''))
            else:
                return StatusResponse(
                    Status.err('Can not stop a not running Program'))
        else:
            return StatusResponse(Status.err('Can not stop unknown Program'))

    else:
        return HttpResponseForbidden()


def program_manage_log(request, program_id):
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
        if ProgramModel.objects.filter(id=program_id).exists():
            program = ProgramModel.objects.get(id=program_id)
            if program.get_log():
                return StatusResponse(Status.ok(''))
            else:
                return StatusResponse(
                    Status.err(
                        'Can not request a log from an offline Client.'))
        else:
            return StatusResponse(
                Status.err('Can not get a log of an unknown program.'))

    else:
        return HttpResponseForbidden()


def program_enable_logging(request, program_id):
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
        if ProgramModel.objects.filter(id=program_id).exists():
            program = ProgramModel.objects.get(id=program_id)
            if program.enable_logging():
                return StatusResponse(Status.ok(''))
            else:
                return StatusResponse(
                    Status.err('Can not enable logging on an offline Client.'))
        else:
            return StatusResponse(
                Status.err('Can not enable logging on an unknown program.'))

    else:
        return HttpResponseForbidden()


def program_disable_logging(request, program_id):
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
        if ProgramModel.objects.filter(id=program_id).exists():
            program = ProgramModel.objects.get(id=program_id)
            if program.disable_logging():
                return StatusResponse(Status.ok(''))
            else:
                return StatusResponse(
                    Status.err(
                        'Can not disable logging on an offline Client.'))
        else:
            return StatusResponse(
                Status.err('Can not disable logging on an unknown program.'))
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
            return StatusResponse(Status.ok(""))
        except KeyError as err:
            return StatusResponse(
                Status.err("Could not find required key {}".format(
                    err.args[0])))
        except TypeError as err:
            return StatusResponse(Status.err(str(err)))
        except ValueError as err:
            return StatusResponse(Status.err(str(err)))
        except ValidationError as err:
            return StatusResponse(Status.err('; '.join(err.messages)))

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
            return StatusResponse(Status.ok(dict(script)))
        except ScriptModel.DoesNotExist:
            return StatusResponse(Status.err("Script does not exist."))

    elif request.method == 'PUT':
        try:
            script_id = int(script_id)
            new_script = Script.from_json(request.body.decode('utf-8'))
            old_script =  Script.from_model(script_id, 'str', 'str', 'str')
            print(new_script.to_json())
            print(old_script.to_json())

            (new_model, _) = ScriptModel.objects.update_or_create(
                id=script_id,
                defaults={"name": new_script.name},
            )

            SGFModel.objects.filter(script=script_id).delete()
            SGPModel.objects.filter(script=script_id).delete()

            for program in new_script.programs:
                SGPModel.objects.create(
                    script=new_model,
                    index=program.index,
                    program=ProgramModel.objects.get(name=program.program),
                )
            for filesystem in new_script.filesystems:
                SGFModel.objects.create(
                    script=new_model,
                    index=filesystem.index,
                    filesystem=FilesystemModel.objects.get(
                        name=filesystem.filesystem,
                        slave=SlaveModel.objects.get(name=filesystem.slave)
                    ),
                )

            return StatusResponse(Status.ok(""))
        except KeyError as err:
            return StatusResponse(
                Status.err("Could not find required key {}".format(
                    err.args[0])))
        except TypeError as err:
            return StatusResponse(Status.err(str(err)))
        except ValueError as err:
            return StatusResponse(Status.err(str(err)))
        except ValidationError as err:
            return StatusResponse(Status.err('; '.join(err.messages)))
        except IntegrityError as err:
            return StatusResponse(Status.err(str(err)))

    elif request.method == 'DELETE':
        ScriptModel.objects.filter(id=script_id).delete()
        return StatusResponse(Status.ok(''))

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
                return StatusResponse(
                    Status.ok("Started script {}".format(script.name)))
            else:
                return StatusResponse(Status.err("A script is still running."))
        except ScriptModel.DoesNotExist:
            return StatusResponse(
                Status.err("The script with the id {} does not exist.".format(
                    script_id)))
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
            LOGGER.info("filesystem: %s", filesystem)

            try:
                filesystem.full_clean()
                # IMPORTANT: remove trailing path seperator (if not the query will not
                # work [the query in filesystem_move])
                filesystem.destination_path = up.remove_trailing_path_seperator(
                    filesystem.destination_path)
                filesystem.source_path = up.remove_trailing_path_seperator(
                    filesystem.source_path)
                form.save()

                return StatusResponse(Status.ok(''))
            except ValidationError as err:
                LOGGER.error("Error while adding filesystem: %s", err)

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
                return StatusResponse(Status.err(error_dict))
        else:
            return StatusResponse(Status.err(form.errors))

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
                        slave = SlaveModel.objects.get(id=int(slave))
                    except ValueError:
                        return StatusResponse(
                            Status.err("Slave has to be an integer."))
            except SlaveModel.DoesNotExist:
                ret_err = "Could not find slave with"
                if slave_str:
                    ret_err += " name `{}`".format(slave)
                else:
                    ret_err += " id `{}`".format(slave)

                ret_err += "."

                return StatusResponse(Status.err(ret_err))

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

        return StatusResponse(Status.ok(list(filesystems)))
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
        filesystem = FilesystemModel.objects.get(id=filesystem_id)
        slave = filesystem.slave

        if slave.is_online:
            if filesystem.is_moved:
                return StatusResponse(
                    Status.err(
                        'Error: Filesystem `{}` is already moved.'.format(
                            filesystem.name)))

            if filesystem.destination_type == 'file':
                lookup_file_name = os.path.basename(filesystem.source_path)
                lookup_file = filesystem.destination_path
                (lookup_dir, _) = os.path.split(filesystem.destination_path)

            elif filesystem.destination_type == 'dir':
                lookup_file_name = os.path.basename(filesystem.source_path)
                lookup_file = os.path.join(filesystem.destination_path,
                                           lookup_file_name)
                lookup_dir = filesystem.destination_path

            query = FilesystemModel.objects.filter(
                ~Q(hash_value__exact='') & ~Q(id=filesystem.id) &
                ((Q(destination_path=lookup_file) & Q(destination_type='file'))
                 | (Q(destination_path=lookup_dir) & Q(destination_type='dir')
                    & (Q(source_path__endswith='/' + lookup_file_name)
                       | Q(source_path__endswith='\\' + lookup_file_name)))))

            if query:
                filesystem_replace = query.get()

                first = Command(
                    method="filesystem_restore",
                    source_path=filesystem_replace.source_path,
                    source_type=filesystem_replace.source_type,
                    destination_path=filesystem_replace.destination_path,
                    destination_type=filesystem_replace.destination_type,
                    backup_ending=FILE_BACKUP_ENDING,
                    hash_value=filesystem_replace.hash_value,
                )

                second = Command(
                    method="filesystem_move",
                    source_path=filesystem.source_path,
                    source_type=filesystem.source_type,
                    destination_path=filesystem.destination_path,
                    destination_type=filesystem.destination_type,
                    backup_ending=FILE_BACKUP_ENDING,
                )

                cmd = Command(
                    method="chain_execution",
                    commands=[dict(first), dict(second)],
                )

                filesystem_replace.command_uuid = first.uuid
                filesystem_replace.save()

                filesystem.command_uuid = second.uuid
                filesystem.save()
            else:
                cmd = Command(
                    method="filesystem_move",
                    source_path=filesystem.source_path,
                    source_type=filesystem.source_type,
                    destination_path=filesystem.destination_path,
                    destination_type=filesystem.destination_type,
                    backup_ending=FILE_BACKUP_ENDING,
                )

                filesystem.command_uuid = cmd.uuid
                filesystem.save()

            # send command to the client
            Group('client_' + str(slave.id)).send({'text': cmd.to_json()})

            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(
                Status.err('Can not move {} because {} is offline!'.format(
                    filesystem.name, slave.name)))
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
        filesystem = FilesystemModel.objects.get(id=filesystem_id)
        slave = filesystem.slave

        if slave.is_online:
            if not filesystem.is_moved:
                return StatusResponse(
                    Status.err('Error: filesystem `{}` is not moved.'.format(
                        filesystem.name)))

            cmd = Command(
                method="filesystem_restore",
                source_path=filesystem.source_path,
                source_type=filesystem.source_type,
                destination_path=filesystem.destination_path,
                destination_type=filesystem.destination_type,
                backup_ending=FILE_BACKUP_ENDING,
                hash_value=filesystem.hash_value,
            )

            # send command to the client
            Group('client_' + str(slave.id)).send({'text': cmd.to_json()})

            filesystem.command_uuid = cmd.uuid
            filesystem.save()

            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(
                Status.err('Can not restore {} because {} is offline!'.format(
                    filesystem.name, slave.name)))
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
        filesystem = FilesystemModel.objects.get(id=filesystem_id)
        if not filesystem.is_moved:
            filesystem.delete()
            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(
                Status.err('The file is still moved. Restore the file first.'))

    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        model = FilesystemModel.objects.get(id=filesystem_id)
        form = FilesystemForm(QueryDict(request.body), instance=model)
        if form.is_valid():
            filesystem = form.save(commit=False)
            try:
                filesystem.full_clean()
                form.save()
                return StatusResponse(Status.ok(''))
            except ValidationError as _:
                error_dict = {
                    'name':
                    ['Filesystem with this Name already exists on this Client.']
                }
                return StatusResponse(Status.err(error_dict))
        else:
            return StatusResponse(Status.err(form.errors))
    else:
        return HttpResponseForbidden()
