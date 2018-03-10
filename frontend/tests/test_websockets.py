"""
TESTCASE NAMING SCHEME:
- every channel has an own class

def test_<Websocket Function>(self):
    pass

<Websocket Function>:
    connect <OUTCOME>
    disconnect <OUTCOME>
    receive <TYPE>? <OUTCOME> <HANDLING>?

    <TYPE>:
        chain_execution
        filesystem_restored
        filesystem_moved
        execute
        online
        get_log

    <OUTCOME>:
        e.g. slave_not_exist
        or success

    <HANDLING>?
        ignore
        error
"""
# pylint: disable=missing-docstring,too-many-public-methods

import json
import string

from random import choice

from django.test import TestCase
from channels import Group
from channels.test import WSClient

from utils import Status, Command

from frontend.models import (
    Slave as SlaveModel,
    Filesystem as FilesystemModel,
    ProgramStatus as ProgramStatusModel,
)

from .factory import (
    SlaveFactory,
    SlaveOnlineFactory,
    ProgramStatusFactory,
    FileFactory,
    MovedFileFactory,
)


class RPCWebsocketTests(TestCase):
    def test_connect_success(self):
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

        Group('client_{}'.format(slave.id)).send(
            {
                'text': 'ok'
            },
            immediately=True,
        )
        self.assertEqual(ws_client.receive(json=False), 'ok')

    def test_connect_slave_not_exists(self):
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

    def test_disconnect_success(self):
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

    def test_disconnect_slave_not_exists(self):
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

    def test_receive_parse_json(self):
        ws_client = WSClient()

        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': "str"},
        )

        self.assertIsNone(ws_client.receive())

        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': {
                "test": "test"
            }},
        )

        self.assertIsNone(ws_client.receive())

    def test_receive_unknown_message_type(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': Status.ok({
                'method': ''
            }).to_json()},
        )

        self.assertIsNone(ws_client.receive())

    def test_receive_no_content(self):
        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
        )
        self.assertIsNone(ws_client.receive())

    def test_receive_online_success(self):
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

    def test_receive_online_slave_not_exists(self):
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

    def test_receive_online_with_error_status(self):
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

    def test_receive_execute_success(self):
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

    def test_receive_execute_slave_not_exists(self):
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

    def test_receive_execute_with_error_status(self):
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

    def test_receive_get_log_success(self):
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

    def test_receive_get_log_with_error_status(self):
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

    def test_receive_get_log_program_not_exists(self):
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

    def test_receive_filesystem_moved_success(self):
        filesystem = FileFactory()

        moved = MovedFileFactory.build()

        error_status = Status.ok({
            'method': 'filesystem_move',
            'result': moved.hash_value,
        })
        error_status.uuid = filesystem.command_uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        query = FilesystemModel.objects.get(id=filesystem.id)
        self.assertEqual(query.hash_value, moved.hash_value)
        self.assertEqual(query.error_code, "")

        self.assertEqual(
            Status.ok({
                'filesystem_status': 'moved',
                'fid': str(filesystem.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_receive_filesystem_moved_with_error_code(self):
        filesystem = FileFactory()

        error_code = 'any kind of string'

        error_status = Status.err({
            'method': 'filesystem_move',
            'result': error_code,
        })

        error_status.uuid = filesystem.command_uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        query = FilesystemModel.objects.get(id=filesystem.id)
        self.assertEqual(query.hash_value, "")
        self.assertEqual(query.error_code, error_code)

        self.assertEqual(
            Status.ok({
                'filesystem_status': 'error',
                'fid': str(filesystem.id),
                'error_code': error_code,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_rceive_filesystem_moved_filesystem_not_exists(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        error_status = Status.ok({
            'method': 'filesystem_move',
            'result': None,
        })

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        self.assertIsNone(webinterface.receive())

    def test_receive_filesystem_restore_success(self):
        filesystem = MovedFileFactory()

        error_status = Status.ok({
            'method': 'filesystem_restore',
            'result': None,
        })

        error_status.uuid = filesystem.command_uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        query = FilesystemModel.objects.get(id=filesystem.id)
        self.assertEqual(query.hash_value, "")
        self.assertEqual(query.error_code, "")

        self.assertEqual(
            Status.ok({
                'filesystem_status': 'restored',
                'fid': str(filesystem.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_receive_filesystem_restore_with_error_code(self):
        filesystem = MovedFileFactory()

        error_code = 'any kind of string'

        error_status = Status.err({
            'method': 'filesystem_restore',
            'result': error_code,
        })

        error_status.uuid = filesystem.command_uuid

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        query = FilesystemModel.objects.get(id=filesystem.id)
        self.assertEqual(query.hash_value, "")
        self.assertEqual(query.error_code, error_code)

        self.assertEqual(
            Status.ok({
                'filesystem_status': 'error',
                'fid': str(filesystem.id),
                'error_code': error_code,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_receive_filesystem_restore_filesystem_not_exists(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        error_status = Status.ok({
            'method': 'filesystem_restore',
            'result': None,
        })

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_status.to_json()},
        )

        self.assertIsNone(webinterface.receive())

    def test_receive_chain_commands_with_error_status(self):
        error_chain = Status.err({
            'method': 'chain_execution',
            'result': None,
        })

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_chain.to_json()},
        )

        self.assertIsNone(webinterface.receive())

    def test_receive_chain_commands_success(self):
        filesystem = FileFactory()

        moved = MovedFileFactory.build()

        error_status1 = Status.ok({
            'method': 'filesystem_move',
            'result': moved.hash_value,
        })
        error_status1.uuid = filesystem.command_uuid

        error_status2 = Status.ok({
            'method': 'filesystem_move',
            'result': moved.hash_value,
        })
        error_status2.uuid = filesystem.command_uuid

        error_chain = Status.ok({
            'method':
            'chain_execution',
            'result': [dict(error_status1),
                       dict(error_status2)],
        })

        #  connect webinterface
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume(
            'websocket.receive',
            path='/commands',
            content={'text': error_chain.to_json()},
        )

        query = FilesystemModel.objects.get(id=filesystem.id)
        self.assertEqual(query.hash_value, moved.hash_value)
        self.assertEqual(query.error_code, "")

        self.assertEqual(
            Status.ok({
                'filesystem_status': 'moved',
                'fid': str(filesystem.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        self.assertEqual(
            Status.ok({
                'filesystem_status': 'moved',
                'fid': str(filesystem.id),
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        self.assertIsNone(webinterface.receive())


class NotificationWebsocketTests(TestCase):
    def test_connect_and_disconnect_success(self):
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


class LogWebsocketTests(TestCase):
    def test_connect_and_disconnect_success(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ws_client = WSClient()
        ws_client.send_and_consume('websocket.connect', path='/logs')
        self.assertIsNone(ws_client.receive())

        msg = Status.ok({
            'log':
            ''.join([
                choice(string.ascii_letters + string.digits)
                for _ in range(500)
            ]),
            'pid':
            choice(string.digits)
        })

        ws_client.send_and_consume(
            'websocket.receive', path='/logs', content={
                'text': msg.to_json()
            })
        self.assertEqual(msg,
                         Status.from_json(json.dumps(webinterface.receive())))
