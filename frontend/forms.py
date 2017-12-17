from django.forms import ModelForm
from .models import Slave as SlaveModel
from .models import Program as ProgramModel
from .models import File as FileModel

class SlaveForm(ModelForm):
    class Meta:
        model = SlaveModel
        fields = '__all__'

class ProgramForm(ModelForm):
    class Meta:
        model = ProgramModel
        fields = ['name','path', 'arguments']

class FileForm(ModelForm):
    class Meta:
        model = FileModel
        fields = ['name','sourcePath', 'destinationPath']
