from django.http import HttpResponseForbidden
from django.http.request import QueryDict
from django.core.exceptions import ValidationError


from .models import Slave as SlaveModel, Program as ProgramModel, ProgramStatus as ProgramStatusModel, SlaveStatus as SlaveStatusModel, Script as ScriptModel, ScriptGraphFiles as SGFModel, ScriptGraphPrograms as SGPModel, File as FileModel
from .scripts import Script


from .forms import SlaveForm, ProgramForm, FileForm
from server.utils import StatusResponse
import json

from channels import Group
from utils.status import Status
from utils import Command
from shlex import split
from django.utils import timezone
from wakeonlan.wol import send_magic_packet


def add_slave(request):
    """
    Answers a POST request to add a new slave
    Parameters
    ----------
    request: HttpRequest
        a POST request containing a SlaveForm
    Returns
    -------
    A HttpResponse with a JSON object which
    contains errors if something is goes
    wrong or is empty on success.
    If the request method is something other
    than POST, then HttpResponseForbidden()
    will be returned.
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


def manage_slave(request, id):
    """
    answers a request to manipulate a slave with
    the given id
    ----------
    request: HttpRequest
        a DELETE request
        or a PUT request (data has to be url encoded)
    id: int
        the id of the slave which will be modified
    Returns
    -------
    A HttpResponse with a JSON object which
    can contain errors.
    If the request method is something other
    than DELETE or PUT, then HttpResponseForbidden()
    will be returned.
    """
    if request.method == 'DELETE':
        # i can't find any exeptions that can be thrown in our case
        SlaveModel.objects.filter(id=id).delete()
        return StatusResponse(Status.ok(''))

    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        model = SlaveModel.objects.get(id=id)
        form = SlaveForm(QueryDict(request.body), instance=model)

        if form.is_valid():
            form.save()
            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(Status.err(form.errors))
    else:
        return HttpResponseForbidden()


def add_program(request):
    """
    Answers a POST request to add a new program
    Parameters
    ----------
    request: HttpRequest
        a POST request containing a ProgramForm
        and a slave_id
    Returns
    -------
    A HttpResponse with a JSON object, which contains
    a status. If the status is 'error' the datafield
    errors contains the errors.
    If the request method is something other
    than POST, then HttpResponseForbidden()
    will be returned.
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


def shutdown_slave(request, id):
    """
    answers a request to shutdown slave with
    the given id
    ----------
    request: HttpRequest
        a GET request
    id: int
        the id of the slave which will be modified
    Returns
    -------
    A HttpResponse with a JSON object which
    can contain errors.
    If the request method is something other
    than GET, then a HttpResponseForbidden()
    will be returned.
    """
    if request.method == 'GET':
        if SlaveModel.objects.filter(id=id).exists():
            slave = SlaveModel.objects.get(id=id)
            if SlaveStatusModel.objects.filter(slave=slave).exists():
                Group('client_' + str(id)).send({
                    'text':
                    Command(method="shutdown").to_json()
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


def wol_slave(request, id):
    """
    answers a request to wake a slave with
    the given id
    ----------
    request: HttpRequest
        a GET request
    id: int
        the id of the slave which will be modified
    Returns
    -------
    A HttpResponse with a JSON object which
    can contain errors.
    If the request method is something other
    than GET, then a HttpResponseForbidden()
    will be returned.
    """
    if request.method == 'GET':
        try:
            send_magic_packet(SlaveModel.objects.get(id=id).mac_address)
        except Exception as err:
            return StatusResponse(Status.err(repr(err)), status=500)
        Group('notifications').send({
            'text':
            json.dumps({
                'message': 'Succesful, Client Start queued'
            })
        })
        return StatusResponse(Status.ok(''))
    else:
        return HttpResponseForbidden()


def manage_program(request, programId):
    """
    answers a request to manipulate a program with
    the given programId from a slave with the given slaveId
    ----------
    request: HttpRequest
        a DELETE request to delete a database entry
        or a PUT request to update a database entry
        or a POST request to execute the program on the slave
    slaveId: int
        the id of the slave
    programId: int
        the id of the program which will be modified
    Returns
    -------
    A HttpResponse with a JSON object which
    can contain errors.
    If the request method is something other
    than DELETE or PUT, then HttpResponseForbidden()
    will be returned.
    """
    if request.method == 'DELETE':
        ProgramModel.objects.filter(id=programId).delete()
        return StatusResponse(Status.ok(''))
    if request.method == 'POST':
        program = ProgramModel.objects.get(id=programId)
        if SlaveStatusModel.objects.filter(slave=program.slave).exists():
            ProgramStatusModel(program=program, started=timezone.now()).save()

            # send command to the client
            Group('client_' + str(program.slave.id)).send({
                'text':
                Command(
                    method="execute",
                    pid=program.id,
                    path=program.path,
                    arguments=split(program.arguments)).to_json()
            })

            # tell webinterface that the program has ended
            Group('notifications').send({
                'text':
                Status.ok({
                    "program_status": "started",
                    "pid": program.id,
                }).to_json()
            })
            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(
                Status.err('Can not start {} because {} is offline!'.format(
                    program.name, program.slave.name)))
    elif request.method == 'PUT':
        # create form from a new QueryDict made from the request body
        # (request.PUT is unsupported) as an update (instance) of the
        # existing slave
        model = ProgramModel.objects.get(id=programId)
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


def manage_script(request, scriptId):
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
                scriptId,
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
    Answers a POST request to add a new file
    Parameters
    ----------
    request: HttpRequest
        a POST request containing a FileForm
        and a slave_id
    Returns
    -------
    A HttpResponse with a JSON object, which contains
    a status. If the status is 'error' the datafield
    errors contains the errors.

    If the request method is something other
    than POST, then HttpResponseForbidden()
    will be returned.
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
    # move file
    if request.method == 'POST':
        file = FileModel.objects.get(id=fileId)
        if SlaveStatusModel.objects.filter(slave=file.slave).exists():
            # Status der Files #TODO...
            Group('client_' + str(file.slave.id)).send({
                'text':
                Command(
                    method="move_file",
                    fid=file.id,
                    sourcePath=file.sourcePath,
                    destinationPath=file.destinationPath).to_json()
            })
            return StatusResponse(Status.ok(''))
        else:
            return StatusResponse(
                Status.err('Can not move {} because {} is offline!'.format(
                    file.name, file.slave.name)))
    else:
        return HttpResponseForbidden()
