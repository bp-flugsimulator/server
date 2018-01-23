#  pylint: disable=C0111
#  pylint: disable=C0103

from uuid import uuid4
import json

from django.test import TestCase
from channels import Group
from channels.test import WSClient

from utils import Status, Command
from frontend.models import (
    Slave as SlaveModel,
    SlaveStatus as SlaveStatusModel,
    ProgramStatus as ProgramStatusModel,
    Program as ProgramModel,
)

class WebsocketTests(TestCase): # pylint: disable=unused-variable
    def test_rpc_commands_fails_unkown_slave(self):
        ws_client = WSClient()
        self.assertRaisesMessage(
            AssertionError,
            "Connection rejected: {'accept': False} != '{accept: True}'",
            ws_client.send_and_consume,
            "websocket.connect",
            path="/commands",
            content={'client': ['0.0.9.0', '00:00:00:00:09:00']},
        )

    def test_rpc_commands(self):
        SlaveModel(
            name="test_rpc_commands",
            ip_address='0.0.10.0',
            mac_address='00:00:00:00:10:00',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_rpc_commands",
            ip_address='0.0.10.0',
            mac_address='00:00:00:00:10:00',
        )

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={'client': ['0.0.10.0', '00:00:00:00:10:00']},
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

        slave.delete()

    def test_ws_rpc_disconnect(self):
        SlaveModel(
            name="test_ws_rpc_disconnect",
            ip_address='0.0.10.1',
            mac_address='00:00:00:00:10:01',
        ).save()

        slave = SlaveModel.objects.get(
            name="test_ws_rpc_disconnect",
            ip_address='0.0.10.1',
            mac_address='00:00:00:00:10:01',
        )

        SlaveStatusModel(slave=slave, command_uuid='abcdefg').save()
        slave_status = SlaveStatusModel.objects.get(slave=slave)
        slave_status.online = True
        slave_status.save()

        #  register program
        ProgramModel(
            slave=slave,
            name='name',
            path='path',
            arguments='',
        ).save()
        program = ProgramModel.objects.get(slave=slave)
        ProgramStatusModel(program=program, command_uuid='abcdefg').save()

        # connect client on /commands
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.connect',
            path='/commands',
            content={
                'client': ['0.0.10.1', '00:00:00:00:10:01']
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
        self.assertFalse(SlaveStatusModel.objects.get(slave=slave).online)

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

        slave.delete()

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

    def test_ws_notifications_receive_fail(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
        )
        self.assertIsNone(ws_client.receive())

    def test_ws_notifications_receive_online(self):
        SlaveModel(
            name="test_ws_notifications_receive_online",
            ip_address='0.0.10.2',
            mac_address='00:00:00:00:10:02',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_online",
            ip_address='0.0.10.2',
            mac_address='00:00:00:00:10:02',
        )

        uuid = uuid4().hex
        SlaveStatusModel(slave=slave, command_uuid=uuid).save()
        expected_status = Status.ok({'method': 'online'})
        expected_status.uuid = uuid

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        # send online answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': expected_status.to_json()},
        )

        self.assertTrue(SlaveStatusModel.objects.get(slave=slave).online)

        # test if a connected message was send on /notifications
        self.assertEqual(
            Status.ok({
                'slave_status': 'connected',
                'sid': str(slave.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        slave.delete()

    def test_ws_notifications_receive_online_status_err(self):
        SlaveModel(
            name="test_ws_notifications_receive_online_status_err",
            ip_address='0.0.10.15',
            mac_address='00:00:00:00:10:15',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_online_status_err",
            ip_address='0.0.10.15',
            mac_address='00:00:00:00:10:15',
        )

        uuid = uuid4().hex
        SlaveStatusModel(slave=slave, command_uuid=uuid).save()
        error_status = Status.err({
            'method': 'online',
            'result': str(Exception('foobar'))
        })
        error_status.uuid = uuid

        # connect webinterface on /notifications
        webinterface = WSClient()
        webinterface.join_group('notifications')

        # send online answer
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={
                'text': error_status.to_json()
            })

        self.assertFalse(SlaveStatusModel.objects.get(slave=slave).online)

        # test if a connected message was send on /notifications
        self.assertEqual(
            Status.err(
                'An error occurred while connecting to client {}!'.format(
                    slave.name)),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        slave.delete()

    def test_ws_notifications_receive_execute(self):
        SlaveModel(
            name="test_ws_notifications_receive_execute",
            ip_address='0.0.10.3',
            mac_address='00:00:00:00:10:03',
        ).save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_execute",
            ip_address='0.0.10.3',
            mac_address='00:00:00:00:10:03',
        )

        ProgramModel(
            name='program', path='path', arguments='', slave=slave).save()

        program = ProgramModel.objects.get(
            name='program',
            path='path',
            arguments='',
            slave=slave,
        )

        uuid = uuid4().hex
        program_status = ProgramStatusModel(program=program, command_uuid=uuid)
        program_status.running = True
        program_status.save()

        expected_status = Status.ok({'method': 'execute', 'result': 0})
        expected_status.uuid = uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.send_and_consume(
            'websocket.connect',
            path='/notifications',
        )

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
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

        slave.delete()

    def test_ws_notifications_receive_execute_status_err(self):
        SlaveModel(
            name="test_ws_notifications_receive_execute_status_err",
            ip_address='0.0.10.33',
            mac_address='00:00:00:00:10:33').save()
        slave = SlaveModel.objects.get(
            name="test_ws_notifications_receive_execute_status_err",
            ip_address='0.0.10.33',
            mac_address='00:00:00:00:10:33')

        ProgramModel(
            name='program',
            path='path',
            arguments='',
            slave=slave,
        ).save()

        program = ProgramModel.objects.get(
            name='program',
            path='path',
            arguments='',
            slave=slave,
        )

        uuid = uuid4().hex
        program_status = ProgramStatusModel(program=program, command_uuid=uuid)
        program_status.running = True
        program_status.save()

        error_status = Status.err({
            'method': 'execute',
            'result': str(Exception('foobar')),
        })
        error_status.uuid = uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': error_status.to_json()},
        )

        query = ProgramStatusModel.objects.get(program=program)
        self.assertFalse(query.running)
        self.assertEqual(query.code, 'foobar')

        #  test if the webinterface gets the error message
        self.assertEqual(
            Status.err(
                'An Exception occurred while trying to execute {}'.format(
                    program.name)),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        slave.delete()

    def test_ws_notifications_receive_unknown_method(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/notifications',
            content={'text': Status.ok({
                'method': ''
            }).to_json()},
        )

        self.assertIsNone(ws_client.receive())
