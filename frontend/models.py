from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# Create your models here.
def validate_ip_address(ip_addr):
    parts = ip_addr.split(".")
    if len(parts) != 4:
        return False
    for item in parts:
        if not 0 <= int(item) <= 255:
            raise ValidationError(
                _('Invalid IP Address: %(ip_addr)s'),
                params={'ip_addr': 'ip_addr'},
                code='invalid_ip',
            )


def validate_mac_address(mac_addr):
    if mac_addr.count(":") != 5:
        return False
    for i in mac_addr.split(":"):
        for j in i:
            if j > "F" or (j < "A" and not j.isdigit()) or len(i) != 2:
                raise ValidationError(
                    _('Invalid MAC Address: %(mac_addr)s'),
                    params={'mac_addr': 'mac_addr'},
                    code='invalid_mac',
                )


class Slave(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=200)
    ip_address = models.CharField(
        unique=True, max_length=200, validators=[validate_ip_address])
    mac_address = models.CharField(
        unique=True, max_length=200, validators=[validate_mac_address])

    def clean(self):
        super(Slave, self).clean()
        self.name = self.name.capitalize()
