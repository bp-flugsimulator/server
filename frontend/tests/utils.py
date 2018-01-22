#  pylint: disable=C0111
#  pylint: disable=C0103

from frontend.models import Slave as SlaveModel

def fill_database_slaves_set_1():
    data_set = [
        SlaveModel(
            name="Slave1",
            ip_address="192.168.2.39",
            mac_address="00:00:00:00:00:01",
        ),
        SlaveModel(
            name="Slave2",
            ip_address="192.168.3.39",
            mac_address="02:00:00:00:00:00",
        ),
        SlaveModel(
            name="Slave3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00",
        ),
        SlaveModel(
            name="Slave4",
            ip_address="192.168.6.39",
            mac_address="00:00:02:00:00:00",
        ),
        SlaveModel(
            name="Slave5",
            ip_address="192.168.7.39",
            mac_address="00:00:00:02:00:00",
        )
    ]

    for data in data_set:
        data.save()

    return data_set
