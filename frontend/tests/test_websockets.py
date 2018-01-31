#  pylint: disable=C0111,C0103

import json

from django.test import TestCase
from channels import Group
from channels.test import WSClient

from utils import Status, Command

from frontend.models import (
    Slave as SlaveModel,
    ProgramStatus as ProgramStatusModel,
)

from .factory import (
    SlaveFactory,
    SlaveOnlineFactory,
    ProgramStatusFactory,
)


class WebsocketTests(TestCase):
    def test_rpc_commands_fails_unknown_slave(self):

        slave = SlaveFactory.build()

        ws_client = WSClient()
        self.assertRaisesMessage(
            AssertionError,
            "Connection rejected: {'accept': False} != '{accept: True}'",
            ws_client.send_and_consume,
            "websocket.connect",
            path="/commands",
            content={'client': [slave.ip_address, slave.mac_address]},
        )

    def test_rpc_commands(self):
        slave = SlaveFactory()

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={'client': [slave.ip_address, slave.mac_address]},
        )

        self.assertEqual(
            Command(method="online"),
            Command.from_json(json.dumps(ws_client.receive())),
        )

        #  test if the client is now part of the right groups
        Group('clients').send({'text': 'ok'}, immediately=True)
        self.assertEqual(ws_client.receive(json=False), 'ok')

        Group('client_{}'.format(slave.id)).send(
            {
                'text': 'ok'
            },
            immediately=True,
        )
        self.assertEqual(ws_client.receive(json=False), 'ok')

    def test_ws_rpc_disconnect(self):
        slave = SlaveOnlineFactory()

        program_status = ProgramStatusFactory(program__slave=slave)
        program = program_status.program

        # connect client on /commands
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={
                'client': [slave.ip_address, slave.mac_address]
            })

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        #  throw away connect repsonse
        ws_client.receive()
        ws_client.send_and_consume('websocket.disconnect', path='/commands')

        #  test if SlaveStatus was to offline
        self.assertFalse(SlaveModel.objects.get(id=slave.id).is_online)

        #  test if the client was removed from the correct groups
        Group('clients').send({'text': 'ok'}, immediately=True)
        self.assertIsNone(ws_client.receive())

        Group('client_{}'.format(slave.id)).send(
            {
                'text': 'ok'
            },
            immediately=True,
        )
        self.assertIsNone(ws_client.receive())

        #  test if program status was removed
        self.assertFalse(
            ProgramStatusModel.objects.filter(program=program).exists())

        #  test if a "disconnected" message has been send to the webinterface
        self.assertEqual(
            Status.ok({
                'slave_status': 'disconnected',
                'sid': str(slave.id)
            }), Status.from_json(json.dumps(webinterface.receive())))

    def test_ws_rpc_disconnect_deleted_slave(self):
        slave = SlaveOnlineFactory()

        program_status = ProgramStatusFactory(program__slave=slave)
        program = program_status.program

        # connect client on /commands
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={
                'client': [slave.ip_address, slave.mac_address]
            })

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        slave.delete()

        #  throw away connect response
        ws_client.receive()
        ws_client.send_and_consume('websocket.disconnect', path='/commands')

        self.assertFalse(SlaveModel.objects.filter(id=slave.id).exists())

        self.assertFalse(
            ProgramStatusModel.objects.filter(program=program).exists())

        #  test if a "disconnected" message has been send to the webinterface
        self.assertIsNone(webinterface.receive())

    def test_ws_notifications_connect_and_ws_disconnect(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        #  test if ws_client is part of 'notifications'
        Group('notifications').send({'text': Status.ok('').to_json()})
        self.assertEqual(
            Status.ok(''),
            Status.from_json(json.dumps(ws_client.receive())),
        )

        ws_client.send_and_consume(
            'websocket.disconnect',
            path='/notifications',
        )

        #  test if ws_client was removed from 'notifications'
        Group('notifications').send({'text': Status.ok('').to_json()})
        self.assertIsNone(ws_client.receive())

    def test_ws_rpc_receive_fail(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
        )
        self.assertIsNone(ws_client.receive())

    def test_ws_rpc_receive_online(self):
        slave = SlaveOnlineFactory(online=False)

        expected_status = Status.ok({'method': 'online'})
        expected_status.uuid = slave.command_uuid

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        # send online answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': expected_status.to_json()},
        )

        self.assertTrue(SlaveModel.objects.get(id=slave.id).is_online)

        # test if a connected message was send on /notifications
        self.assertEqual(
            Status.ok({
                'slave_status': 'connected',
                'sid': str(slave.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_ws_rpc_receive_online_delted_slave(self):
        slave = SlaveOnlineFactory(online=False)

        expected_status = Status.ok({'method': 'online'})
        expected_status.uuid = slave.command_uuid

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        slave.delete()

        # send online answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': expected_status.to_json()},
        )

        self.assertFalse(SlaveModel.objects.filter(id=slave.id).exists())

        # test if a connected message was send on /notifications
        self.assertIsNone(webinterface.receive())

    def test_ws_rpc_receive_online_status_err(self):
        slave = SlaveOnlineFactory(online=False)

        error_status = Status.err({
            'method': 'online',
            'result': str(Exception('foobar'))
        })

        error_status.uuid = slave.command_uuid

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        # send online answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={
                'text': error_status.to_json()
            })

        self.assertFalse(SlaveModel.objects.get(id=slave.id).is_online)

        # test if a connected message was send on /notifications
        self.assertEqual(
            Status.err(
                'An error occurred while connecting to client {}!'.format(
                    slave.name)),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_ws_rpc_receive_execute(self):
        program_status = ProgramStatusFactory(running=True)
        program = program_status.program

        expected_status = Status.ok({'method': 'execute', 'result': 0})
        expected_status.uuid = program_status.command_uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': expected_status.to_json()},
        )

        query = ProgramStatusModel.objects.filter(program=program, code=0)
        self.assertTrue(query.count() == 1)
        self.assertFalse(query.first().running)

        #  test if the webinterface gets the "finished" message
        self.assertEqual(
            Status.ok({
                'program_status': 'finished',
                'pid': str(program.id),
                'code': 0,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_ws_rpc_receive_execute_delete_slave(self):
        program_status = ProgramStatusFactory(running=True)
        program = program_status.program

        expected_status = Status.ok({'method': 'execute', 'result': 0})
        expected_status.uuid = program_status.command_uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        program.delete()

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': expected_status.to_json()},
        )

        self.assertFalse(
            ProgramStatusModel.objects.filter(program=program).exists())

        #  test if the webinterface gets the "finished" message
        self.assertIsNone(webinterface.receive())

    def test_ws_rpc_receive_execute_status_err(self):
        program_status = ProgramStatusFactory(running=True)
        program = program_status.program

        error_status = Status.err({
            'method': 'execute',
            'result': str(Exception('foobar')),
        })
        error_status.uuid = program_status.command_uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        query = ProgramStatusModel.objects.get(program=program)
        self.assertFalse(query.running)
        self.assertEqual(query.code, 'foobar')

        #  test if the webinterface gets the error message
        self.assertEqual(
            Status.ok({
                'program_status': 'finished',
                'pid': str(program.id),
                'code': 'foobar',
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_ws_rpc_receive_log(self):
        program_status = ProgramStatusFactory(running=True)
        program = program_status.program

        error_status = Status.ok({
            'method': 'get_log',
            'result': {
                'log': 'this is the content of a logfile',
                'uuid': program_status.command_uuid,
            },
        })

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        #  test if the webinterface gets the error message
        self.assertEqual(
            Status.ok({
                'log': 'this is the content of a logfile',
                'pid': str(program.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_ws_rpc_receive_log_status_err(self):
        error_status = Status.err({
            'method': 'get_log',
            'result': str(Exception('foobar')),
        })

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        #  test if the webinterface gets the error message
        self.assertEqual(
            Status.err('An error occured while reading a log file!'),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_ws_rpc_receive_log_unknown_program(self):
        error_status = Status.ok({
            'method': 'get_log',
            'result': {
                'log': '',
                'uuid': '0'
            },
        })

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        #  test if the webinterface gets the error message
        self.assertEqual(
            Status.err('Received log from unknown program!'),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_ws_rpc_receive_unknown_method(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': Status.ok({
                'method': ''
            }).to_json()},
        )

        self.assertIsNone(ws_client.receive())
