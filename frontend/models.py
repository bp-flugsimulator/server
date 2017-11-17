from django.db import models
from django.core.exceptions import ValidationError


# Create your models here.
def validate_ip_address(ip_addr):
    parts = ip_addr.split(".")
    if len(parts) != 4:
        return False
    for item in parts:
        if not 0 <= int(item) <= 255:
            raise ValidationError(
                "{} is not a valid IP Address".format(ip_addr))


def validate_mac_address(mac_addr):
    if mac_addr.count(":") != 5:
        return False
    for i in mac_addr.split(":"):
        for j in i:
            if j > "F" or (j < "A" and not j.isdigit()) or len(i) != 2:
                raise ValidationError(
                    "{} is not a valid MAC Address".format(mac_addr))


class Slave(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=200)
    ip_address = models.CharField(
        unique=True, max_length=200, validators=[validate_ip_address])
    mac_address = models.CharField(
        unique=True, max_length=200, validators=[validate_mac_address])
