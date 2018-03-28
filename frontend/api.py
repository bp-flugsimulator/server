"""
This module contains functions that handle requests on the REST API. Every API
handler function has an HTTP METHOD attribute in the doc string where more
information about a supported HTTP method can be found.
"""
import logging
import platform
import sched, threading
import subprocess

from django.http import HttpResponseForbidden
from django.http.request import QueryDict
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from utils import Status
from utils.typecheck import ensure_type
import utils.path as up

from server.utils import StatusResponse

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

from .errors import (
    FsimError,
    SlaveNotExistError,
    ProgramNotExistError,
    FilesystemNotExistError,
    SimultaneousQueryError,
    ScriptRunningError,
    ScriptNotExistError,
)

from frontend import controller

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
    """
    This functions removes code duplication for `script_entry` and
    `script_set`. The logic for the PUT and POST method inside these functions
    are identical. For more information take a look at `script_entry` or
    `script_set`
    """
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


def convert_str_to_bool(string):
    """
    Converts a string into a boolean by checking common patterns.  If no
    pattern is matching the default (False) is returned. Common string patterns
    are for the boolean true are on of ('yes', 'true', '1', 't', 'y').

    Parameters
    ----------
        string: str
            The string which will be converted.
    Returns
    -------
        bool:
            If one of the patterns was found in the string.

    Raises
    ------
        TypeError:
            If string is not a str instance.
    """
    ensure_type("string", string, str)
    return string.lower() in ('yes', 'true', '1', 't', 'y')


def slave_set(request):
    """
    Process requests on a set of `SlaveModel`s.

    HTTP Methods
    ------------
        POST:
            Adds a new `SlaveModel` to the database.
        GET: query with (?q=None)
            Searches for the name which is like ".*q.*"
        GET: query with (?programs=False)
            If this is True, then all `SlaveModel`s are returned which have a
            `ProgramModel`.
        GET: query with (?filesystems=False)
            If this is True, then all `SlaveModel`s are returned which have a
            `FilesystemModel`.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
        form = SlaveForm(request.POST)
        if form.is_valid():
            form.save()
            return StatusResponse.ok('')
        return StatusResponse.err(form.errors)
    elif request.method == 'GET':
        query = request.GET.get('q', None)

        programs = request.GET.get('programs', '')
        programs = convert_str_to_bool(programs)

        filesystems = request.GET.get('filesystems', '')
        filesystems = convert_str_to_bool(filesystems)

        if query is not None:
            slaves = SlaveModel.objects.filter(
                name__contains=query).values_list(
                    "name",
                    flat=True,
                )
        elif programs or filesystems:
            if programs and filesystems:
                return StatusResponse(
                    SimultaneousQueryError('filesystems', 'programs'))
            elif programs:
                slaves = SlaveModel.with_programs()
            elif filesystems:
                slaves = SlaveModel.with_filesystems()
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
    Process requests for a single `SlaveModel`s.

    HTTP Methods
    ------------
        DELETE:
            Removes the specified entry (in the URL) from the database.
        PUT:
            Updates the specified entry (in the URL) in the database.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'DELETE':
        try:
            SlaveModel.objects.get(id=slave_id).delete()
            return StatusResponse.ok('')
        except SlaveModel.DoesNotExist as err:
            return StatusResponse(SlaveNotExistError(err, slave_id))

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
    Processes an method invocation (shutdown) for an `SlaveModel`.(see
    @frontend.controller.slave_shutdown)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `SlaveModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
        try:
            slave = SlaveModel.objects.get(id=slave_id)
            controller.slave_shutdown(slave)
            return StatusResponse.ok('')
        except FsimError as err:
            return StatusResponse(err)
        except SlaveModel.DoesNotExist as err:
            return StatusResponse(SlaveNotExistError(err, slave_id))

    else:
        return HttpResponseForbidden()


def slave_wol(request, slave_id):
    """
    Processes an method invocation (wol) for an `SlaveModel`. (see
    @frontend.controller.slave_wake_on_lan)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `SlaveModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
        try:
            slave = SlaveModel.objects.get(id=slave_id)
            slave_wake_on_lan(slave)
            return StatusResponse.ok('')
        except SlaveModel.DoesNotExist as err:
            return StatusResponse(SlaveNotExistError(err, slave_id))
    else:
        return HttpResponseForbidden()


def program_set(request):
    """
    Process requests on a set of `ProgramModel`s.

    HTTP Methods
    ------------
        POST:
            Adds a new `ProgramModel` to the database.
        GET: query with (?q=None)
            Searches for the name which is like ".*q.*"
        GET: query with (?slave=None&is_string=False)
            Searches for all `ProgramModel`s which belong to the given `slave`.
            Where `is_string` specifies if the given `slave` is an unique name
            or and unique index.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
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
        query = request.GET.get('q', None)

        slave = request.GET.get('slave', None)
        slave_str = request.GET.get('is_string', False)

        if query is not None:
            progs = ProgramModel.objects.filter(
                name__contains=query).values_list(
                    "name",
                    flat=True,
                )
        elif slave is not None:
            if slave_str:
                slave_str = convert_str_to_bool(slave_str)

            try:
                slave = SlaveModel.from_identifier(slave, slave_str)
            except FsimError as err:
                return StatusResponse(err)
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
    Process requests for a single `ProgramModel`s.

    HTTP Methods
    ------------
        DELETE:
            Removes the specified entry (in the URL) from the database.
        PUT:
            Updates the specified entry (in the URL) in the database.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'DELETE':
        try:
            ProgramModel.objects.get(id=program_id).delete()
            return StatusResponse.ok('')
        except ProgramModel.DoesNotExist as err:
            return StatusResponse(ProgramNotExistError(err, program_id))
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
    Processes an method invocation (start) for an `ProgramModel`.(see
    @frontend.controller.prog_start)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `ProgramModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
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
    Processes an method invocation (stop) for an `ProgramModel`. (see
    @frontend.controller.prog_stop)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `ProgramModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
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


def program_log_entry(request, program_id):
    """
    Process requests for a single `ProgramModel`s for the log attribute.

    HTTP Methods
    ------------
        GET:
            Fetches the log entry from the related `SlaveModel`.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
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


def program_log_enable(request, program_id):
    """
    Processes an method invocation (log_enable) for an `ProgramModel`. (see
    @frontend.controller.prog_log_enable)

    HTTP Methods
    ------------
        POST:
            Notifies the `SlaveModel` to send logs for this `ProgramModel`.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
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


def program_log_disable(request, program_id):
    """
    Processes an method invocation (log_disable) for an `ProgramModel`. (see
    @frontend.controller.prog_log_disable)

    HTTP Methods
    ------------
        POST:
            Notifies the `SlaveModel` to stop the sending process for logs
            for this `ProgramModel`.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
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
    Process requests on a set of `ScriptModel`s.

    HTTP Methods
    ------------
        POST:
            Adds a new `ScriptModel` to the database.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
        return script_put_post(request.body.decode('utf-8'), None)
    else:
        return HttpResponseForbidden()


def script_entry(request, script_id):
    """
    Process requests for a single `ScriptEntry`s.

    HTTP Methods
    ------------
        GET: query (with ?slaves=int&programs=int&filesystem=int)
            Returns this `ScriptModel` as a JSON encoded string where
            `SlavesModel`, `ProgramModel` and `FilesystemModel` encoded as str
            or int (specified by &slaves=str, &programs=str, &filesystem=str).
        DELETE:
            Removes the specified entry (in the URL) from the database.
        PUT:
            Updates the specified entry (in the URL) in the database.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
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
        except FsimError as err:
            return StatusResponse(err)
        except ScriptModel.DoesNotExist as err:
            return StatusResponse(ScriptNotExistError(err, script_id))
    elif request.method == 'PUT':
        return script_put_post(request.body.decode('utf-8'), int(script_id))
    elif request.method == 'DELETE':
        try:
            ScriptModel.objects.get(id=script_id).delete()
            return StatusResponse.ok('')
        except ScriptModel.DoesNotExist as err:
            return StatusResponse(ScriptNotExistError(err, script_id))
    else:
        return HttpResponseForbidden()


def script_copy(request, script_id):
    """
    Processes an method invocation (copy) for an `ScriptModel`. (see
    @frontend.controller.script_copy)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `ScriptModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
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
    Processes an method invocation (run) for an `ScriptModel`. (see
    @frontend.controller.script_run)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `ScriptModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """

    if request.method == 'POST':
        try:
            script = ScriptModel.objects.get(id=script_id)
            # only allow the start of a script if the old one is finished
            script_running = ScriptModel.objects.filter(
                is_running=True, is_initialized=True).exists()

            if not script_running:
                FSIM_CURRENT_SCHEDULER.start(script.id)
                FSIM_CURRENT_SCHEDULER.notify()
                return StatusResponse.ok('')
            else:
                return StatusResponse(ScriptRunningError(str(script.name)))
        except ScriptModel.DoesNotExist as err:
            return StatusResponse(ScriptNotExistError(err, script_id))
    else:
        return HttpResponseForbidden()


def script_stop(request):
    """
    Processes an method invocation (stop) for a `ScriptModel` (see
    @frontend.sheduler.stop_loop)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `ScriptModel`

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """

    if request.method == 'POST':
        FSIM_CURRENT_SCHEDULER.stop()
        FSIM_CURRENT_SCHEDULER.notify()
        return StatusResponse.ok('')
    else:
        return HttpResponseForbidden()


def script_set_default(request, script_id):
    """
    Processes an method invocation (set_default) for a `ScriptModel`.
    HTTP Methods
    ------------
        POST:
            Invokes the method for the `ScriptModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
        ScriptModel.set_last_started(script_id)
        return StatusResponse.ok('')
    else:
        return HttpResponseForbidden()


def filesystem_set(request):
    """
    Process requests on a set of `FilesystemModel`s.

    HTTP Methods
    ------------
        POST:
            Adds a new `FilesystemModel` to the database.
        GET: query with (?q=None)
            Searches for the name which is like ".*q.*"
        GET: query with (?slave=None&is_string=False)
            Searches for all `FilesystemModel`s which belong to the given `slave`.
            Where `is_string` specifies if the given `slave` is an unique name or
            and unique index.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
        form = FilesystemForm(request.POST or None)

        if form.is_valid():
            filesystem = form.save(commit=False)
            filesystem.slave = form.cleaned_data['slave']

            try:
                filesystem.full_clean()
                # IMPORTANT: remove trailing path seperator (if not the query
                # will not work [the query in filesystem_move])
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
        query = request.GET.get('q', None)

        slave = request.GET.get('slave', None)
        slave_str = request.GET.get('is_string', False)

        if query is not None:
            filesystems = FilesystemModel.objects.filter(
                name__contains=query).values_list(
                    "name",
                    flat=True,
                )
        elif slave is not None:
            if slave_str:
                slave_str = convert_str_to_bool(slave_str)

            try:
                slave = SlaveModel.from_identifier(slave, slave_str)
            except FsimError as err:
                return StatusResponse(err)
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
    Processes an method invocation (move) for an `FilesystemModel`. (see
    @frontend.controller.filesystem_move)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `FilesystemModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
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
    Processes an method invocation (restore) for an `FilesystemModel`. (see
    @frontend.controller.filesystem_restore)

    HTTP Methods
    ------------
        POST:
            Invokes the method for the `FilesystemModel` (which is
            specified in the URL).

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
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
    Process requests for a single `FilesystemModel`s.

    HTTP Methods
    ------------
        DELETE:
            Removes the specified entry (in the URL) from the database.
        PUT:
            Updates the specified entry (in the URL) in the database.

    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
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


def scope_operations(request):
    """
    Process requests to shutdown all clients

    HTTP Methods
    ------------
        POST:
            Stops all programs, resets the filesystem and shuts down every client
    Parameters
    ----------
        request: HttpRequest
            The request which should be processed.

    Returns
    -------
        HttpResponse:
            If the HTTP method is not supported, then an
            `HttpResponseForbidden` is returned.
    """
    if request.method == 'POST':
        FSIM_CURRENT_SCHEDULER.stop()
        FSIM_CURRENT_SCHEDULER.notify()
        t = ShutdownThread(request.POST['scope'])
        t.start()
        return StatusResponse.ok('')
    else:
        return HttpResponseForbidden()


class ShutdownThread(threading.Thread):
    def __init__(self, scope):
        threading.Thread.__init__(self)
        self.scope = scope

    def run(self):  # pragma: no cover
        s = sched.scheduler()
        programs = ProgramModel.objects.all()
        programs = filter(lambda x: x.is_running, programs)
        delay = 0
        for program in programs:
            s.enter(delay, 2, prog_stop, argument=(program, ))
            delay += 1
        if self.scope == 'programs':
            s.run()
            return
        filesystems = FilesystemModel.objects.all()
        filesystems = filter(lambda x: x.is_moved, filesystems)
        delay += 10
        for filesystem in filesystems:
            s.enter(delay, 1, fs_restore, argument=(filesystem, ))
        if self.scope == 'filesystem':
            s.run()
            return
        slaves = SlaveModel.objects.all()
        slaves = filter(lambda x: x.is_online, slaves)
        delay += 8
        for slave in slaves:
            s.enter(delay, 3, controller.slave_shutdown, argument=(slave, ))
            delay += 1
        if self.scope == 'clients':
            s.run()
            return
        s.run()

        if platform.system() == "Windows":
            subprocess.run(['shutdown', '-s', '-t', '0'])
        else:
            subprocess.run(['shutdown', '-h now'])
