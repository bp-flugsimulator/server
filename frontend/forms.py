from django.forms import ModelForm
from .models import Slave as SlaveModel
from .models import Program as ProgramModel

class SlaveForm(ModelForm):
    class Meta:
        model = SlaveModel
        fields = '__all__'

class ProgramForm(ModelForm):
    class Meta:
        model = ProgramModel
        fields = ['name','command']
