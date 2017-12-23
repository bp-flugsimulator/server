from django.forms import ModelForm, ModelChoiceField, HiddenInput
from .models import Slave as SlaveModel
from .models import Program as ProgramModel


class SlaveForm(ModelForm):
    class Meta:
        model = SlaveModel
        fields = '__all__'


class ProgramForm(ModelForm):
    slave = ModelChoiceField(
        queryset=SlaveModel.objects.all(),
        widget=HiddenInput(),
    )

    class Meta:
        model = ProgramModel
        fields = ['name', 'path', 'arguments']
