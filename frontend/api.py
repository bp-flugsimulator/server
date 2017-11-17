from django.http import HttpResponseForbidden, HttpResponseRedirect
from .models import Slave as SlaveModel
from .forms import SlaveForm

def addSlave(request):
    if request.method == 'POST':
        form = SlaveForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            ip = form.cleaned_data['ip_address']
            mac = form.cleaned_data['mac_address']
            SlaveModel(name=name, ip_address=ip,mac_address=mac).save()
        return HttpResponseRedirect("/slaves/")
    else:
        return HttpResponseForbidden
