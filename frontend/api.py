"""
This module contains all functions that handle requests on the REST api.
"""

from shlex import split

from django.http import HttpResponseForbidden
from django.http.request import QueryDict
from django.core.exceptions import ValidationError
from channels import Group
from utils.status import Status
from utils import Command
from wakeonlan.wol import send_magic_packet
from server.utils import StatusResponse

from .models import Slave as SlaveModel, Program as ProgramModel, ProgramStatus as ProgramStatusModel, SlaveStatus as SlaveStatusModel, Script as ScriptModel, ScriptGraphFiles as SGFModel, ScriptGraphPrograms as SGPModel, File as FileModel
from .scripts import Script


from .forms import SlaveForm, ProgramForm, FileForm

from .consumers import notify


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
            if SlaveStatusModel.objects.filter(
                    slave=slave) and slave.slavestatus.online:
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
            send_magic_packet(SlaveModel.objects.get(id=slave_id).mac_address)
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
        slave = program.slave
        if SlaveStatusModel.objects.filter(
                slave=slave) and slave.slavestatus.online:
            cmd = Command(
                method="execute",
                path=program.path,
                arguments=split(program.arguments))

            # send command to the client
            Group('client_' + str(program.slave.id)).send({
                'text': cmd.to_json()
            })

            # tell webinterface that the program has started
            Group('notifications').send({
                'text':
                Status.ok({
                    "program_status": "started",
                    "pid": program.id,
                }).to_json()
            })

            # create status entry
            ProgramStatusModel(program=program, command_uuid=cmd.uuid).save()

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


def manage_script(request, script_id):
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

def manage_file(request, fileId):
    """
    Manages the file with the fileId.

    Arguments
    ----------
    request: HttpRequest
        a DELETE #TODO
        or a PUT  #TODO
        or a POST request to copy the file with fileId
            from sourcePath to destinationPath
    fileId: int
        the ID of the file

    Returns
    -------
    A HttpResponse with a JSON object which
    can contain errors.
    """
    # if request.method == 'DELETE':
        #TODO
    if request.method == 'POST':
        file = FileModel.objects.get(id=fileId)
        slave = file.slave
        if SlaveStatusModel.objects.filter(slave=slave):
            cmd = Command(
                    method="move_file",    # move file
                    sourcePath=file.sourcePath,
                    destinationPath=file.destinationPath)

            # send command to the client
            Group('client_' + str(slave.id)).send({'text': cmd.to_json()})

            # tell webinterface that the file was moved
            Group('notifications').send({
                'text':
                Status.ok({
                    "file_status": "moved",
                    "pid": file.id
                }).to_json()
            })

            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(
                Status.err('Can not move {} because {} is offline!'.format(
                    file.name, slave.name)))
    else:
        return HttpResponseForbidden()
