"""
This module contains all functions that handle requests on the REST api.
"""
import logging

from django.http import HttpResponseForbidden
from django.http.request import QueryDict
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from channels import Group
from utils import Status, Command
from server.utils import StatusResponse

from .models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    Script as ScriptModel,
    File as FileModel,
)

from .scripts import Script
from .forms import SlaveForm, ProgramForm, FileForm
from .consumers import notify

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
        return StatusResponse(
            Status.ok(
                list(
                    set([
                        obj['name']
                        for obj in SlaveModel.objects.filter(
                            name__contains=query).values("name")
                    ]))))
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


def program_get_log(request, program_id):
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
                    Status.err('Can not request a log from an offline Client.')
                )
        else:
            return StatusResponse(Status.err('Can not get a log of an unknown program.'))

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
        except TypeError:
            return StatusResponse(Status.err("Wrong array items."))
        except ValueError as err:
            return StatusResponse(Status.err(str(err)))
        except IntegrityError:
            return StatusResponse(
                Status.err("Script with that name already exists."))
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
            # adds ?slaves=int&program_key=int&file_key=int to the URL
            # to allow a dynamic format for the json string
            slave_key = request.GET.get('slaves', 'int')
            program_key = request.GET.get('programs', 'int')
            file_key = request.GET.get('files', 'int')

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

            if file_key != 'str' and file_key != 'int':
                return StatusResponse(
                    Status.err(
                        "files only allow str or int. (given {})".format(
                            file_key)))

            script = Script.from_model(
                script_id,
                slave_key,
                program_key,
                file_key,
            )
            return StatusResponse(Status.ok(dict(script)))
        except ScriptModel.DoesNotExist:
            return StatusResponse(Status.err("Script does not exist."))

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


def add_file(request):
    """
    Process POST requests which adds new FileModel and GET requests to query
    for FileModel which contains the query string.

    Parameters
    ----------
        request: HttpRequest

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'POST':
        form = FileForm(request.POST or None)

        if form.is_valid():
            file = form.save(commit=False)
            file.slave = form.cleaned_data['slave']
            try:
                file.full_clean()
                form.save()
                return StatusResponse(Status.ok(''))
            except ValidationError as _:
                error_dict = {
                    'name':
                    ["File with this Name already exists on this Client."]
                }
                return StatusResponse(Status.err(error_dict))
        else:
            return StatusResponse(Status.err(form.errors))
    elif request.method == 'GET':
        # the URL takes an argument with ?q=<string>
        # e.g. /files?q=test
        query = request.GET.get('q', '')

        return StatusResponse(
            Status.ok(
                list(
                    set([
                        obj['name']
                        for obj in FileModel.objects.filter(
                            name__contains=query).values("name")
                    ]))))
    else:
        return HttpResponseForbidden()


def manage_file(request, file_id):
    """
    Process DELETE, PUT and POST requests for the FileModel ressource.

    Parameters
    ----------
        request: HttpRequest
        fileId: Unique identifier of a file

    Returns
    -------
        A StatusResponse or HttpResponseForbidden if the request method was
        other than GET.
    """
    if request.method == 'DELETE':
        FileModel.objects.filter(id=file_id).delete()
        return StatusResponse(Status.ok(''))

