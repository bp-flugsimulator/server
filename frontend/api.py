from django.http import HttpResponseForbidden, JsonResponse
from .models import Slave as SlaveModel
from .forms import SlaveForm


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
            name = form.cleaned_data['name']
            ip = form.cleaned_data['ip_address']
            mac = form.cleaned_data['mac_address']
            model = SlaveModel(name=name, ip_address=ip,mac_address=mac)
            model.save()
        return JsonResponse(form.errors)
    else:
        return HttpResponseForbidden()

def manage_slave(request, id):
    """
    answers a request to manipulate a slave with
    the given id
    ----------
    request: HttpRequest
        a DELETE request
    id: int
        the id of the slave which will be modified
    Returns
    -------
    A HttpResponse with a JSON object which
    contains currently nothing.
    If the request method is something other
    than DELETE, then HttpResponseForbidden()
    will be returned.
    """
    if request.method == 'DELETE':
        SlaveModel.objects.filter(id=id).delete() #i can't find any exeptions that can be thrown in our case
        return JsonResponse({})
    else:
        return HttpResponseForbidden()
