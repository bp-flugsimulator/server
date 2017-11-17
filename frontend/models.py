from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


# Create your models here.
def validate_mac_address(mac_addr):
    """
    Validates a given MAC address.

    This functions checks if a given string is a valid
    MAC address.

    Parameters
    ----------
    mac_addr : str
        MAC address

    Returns
    -------
    nothing

    Exception
    ---------
    Raises an ValidationError if the given string is not
    a valid MAC address.
    """

    def ishex(char):
        return (char <= 'F' and char >= 'A') or (char <= 'f' and char >= 'a')

    parts = mac_addr.split(":")
    if len(parts) == 6:
        for part in parts:
            for char in part:
                if (not ishex(char) and not char.isdigit()) or len(part) != 2:
                    raise ValidationError(
                        _('Invalid MAC Address (not allowed symbols): %(mac_addr)s'
                          ),
                        params={'mac_addr': 'mac_addr'},
                        code='invalid_mac_sym',
                    )
    else:
        raise ValidationError(
            _('Invalid MAC Address (too few parts): %(mac_addr)s'),
            params={'mac_addr': 'mac_addr'},
            code='invalid_mac_few',
        )


class Slave(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=200)
    ip_address = models.GenericIPAddressField(unique=True)
    mac_address = models.CharField(
        unique=True, max_length=200, validators=[validate_mac_address])
