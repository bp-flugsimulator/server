from django.http import HttpResponseForbidden, HttpResponseRedirect
from .models import Slave as SlaveModel
from .forms import SlaveForm
from django.db.utils import DatabaseError

from django.contrib import messages


def addSlave(request):
    if request.method == 'POST':
        form = SlaveForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            ip = form.cleaned_data['ip_address']
            mac = form.cleaned_data['mac_address']
            try:
                SlaveModel(name=name, ip_address=ip,mac_address=mac).save()
            except DatabaseError as err:
                messages.error(request, err)
        else:
            errormsg = ''
            for value in form.errors.as_data().values():
                errormsg += str(value[0])\
                    .replace('\'','')\
                    .replace('[','')\
                    .replace(']','') + ' '
            messages.error(request, errormsg)
        return HttpResponseRedirect("/slaves/")
    else:
        return HttpResponseForbidden
