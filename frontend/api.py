from django.http import HttpResponseForbidden
from django.http.request import QueryDict
from django.core.exceptions import ValidationError

from .models import Slave as SlaveModel, Program as ProgramModel

from .forms import SlaveForm, ProgramForm
from server.utils import StatusResponse

import json

from channels import Group
from .queue import wake_Slave
from utils.status import Status


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
    Answers a POST request to add a new slave
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
            program.slave = SlaveModel.objects.get(id=request.POST["slave_id"])
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
            wake_Slave(SlaveModel.objects.get(id=id).mac_address)
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
        a DELETE request
        or a PUT request
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
