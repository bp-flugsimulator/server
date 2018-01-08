from django.forms import ModelForm, ModelChoiceField, HiddenInput
from .models import Slave as SlaveModel
from .models import Program as ProgramModel
from .models import File as FileModel


class SlaveForm(ModelForm):
    class Meta:
        model = SlaveModel
        fields = ['name', 'ip_address', 'mac_address']


class ProgramForm(ModelForm):
    slave = ModelChoiceField(
        queryset=SlaveModel.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        model = ProgramModel
        fields = ['name', 'path', 'arguments']


class FileForm(ModelForm):

    slave = ModelChoiceField(
        queryset=SlaveModel.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        model = FileModel
        fields = ['name', 'sourcePath', 'destinationPath']
