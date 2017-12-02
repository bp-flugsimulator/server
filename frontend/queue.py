from django_q.tasks import async

from wakeonlan.wol import send_magic_packet


def wake_Slave(mac_address):
    """
    wake a slave with a given
    mac address
    ----------
    mac_address: str
        the mac address of a slave to wake
    Returns
    -------
    """
    async(send_magic_packet, mac_address)
