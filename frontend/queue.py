from django_q.tasks import async

from wakeonlan.wol import send_magic_packet


def wakeSlave(mac_address):
    async(send_magic_packet, mac_address)
