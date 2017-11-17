from django.forms import ModelForm
from .models import Slave as SlaveModel

class SlaveForm(ModelForm):
    class Meta:
        model = SlaveModel
        fields = '__all__'