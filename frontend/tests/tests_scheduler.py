"""
Test file for scheduler.py
"""
import json
import asyncio
from uuid import uuid4

from utils import Status
from .testcases import SchedulerTestCase

from channels.test import WSClient

from frontend.models import (
    Slave as SlaveModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
    ScriptGraphPrograms as SGP,
    Script as ScriptModel,
)

from frontend.scheduler import Scheduler, SchedulerStatus

from frontend.errors import SlaveOfflineError


class SchedulerTests(SchedulerTestCase):
    def setUp(self):
        super().setUp()

        script = ScriptModel(name="t1")
        script.save()

        slave1 = SlaveModel(
            name="test_slav21",
            ip_address="0.1.2.0",
            mac_address="01:01:01:00:00100",
            online=False,
        )
        slave1.save()

        slave2 = SlaveModel(
            name="test_sl1ve2",
            ip_address="0.1.2.1",
            mac_address="00:02:01:01:00:00",
            online=False,
        )
        slave2.save()

        prog1 = ProgramModel(name="test_program1", path="none", slave=slave1)
        prog1.save()

        prog2 = ProgramModel(
            name="test_program2",
            path="none",
            slave=slave2,
            start_time=1,
        )
        prog2.save()

        sgp1 = SGP(index=0, program=prog1, script=script)
        sgp1.save()

        sgp2 = SGP(index=2, program=prog2, script=script)
        sgp2.save()

        self.sched = Scheduler()
        self.script = script
        self.slave1 = slave1
        self.slave2 = slave2
        self.prog1 = prog1
        self.prog2 = prog2

    def tearDown(self):
        self.sched.stop()

        self.script.delete()
        self.slave1.delete()
        self.slave2.delete()

        self.assertFalse(ScriptModel.objects.all().exists())
        self.assertFalse(SlaveModel.objects.all().exists())
        self.assertFalse(ProgramStatusModel.objects.all().exists())

    def test_start(self):
        self.assertTrue(self.sched.start(self.script.id))
        self.assertTrue(self.sched.is_running())

        self.assertFalse(self.sched.start(self.script.id))
        self.assertFalse(self.sched.should_stop())

        self.sched.stop()
        self.assertTrue(self.sched.should_stop())
        self.assertFalse(self.sched.is_running())

    def test_state_waiting_slaves(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ScriptModel.objects.filter(id=self.script.id).update(
            is_running=True,
            is_initialized=True,
            current_index=-1,
        )

        self.sched._Scheduler__index = -1
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_SLAVES

        self.sched._Scheduler__state_wait_slaves()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_SLAVES,
        )

        self.slave1.online = True
        self.slave1.save()

        self.sched._Scheduler__state_wait_slaves()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_SLAVES,
        )

        self.slave2.online = True
        self.slave2.save()

        self.sched._Scheduler__state_wait_slaves()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.NEXT_STEP,
        )

        self.assertIsNone(webinterface.receive())

    def test_state_init(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        ScriptModel.objects.filter(id=self.script.id).update(
            is_running=True,
            is_initialized=True,
            current_index=-1,
        )

        self.sched._Scheduler__index = -1
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__state = SchedulerStatus.INIT

        self.sched._Scheduler__state_init()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_SLAVES,
        )

        msg1 = Status.from_json(json.dumps(webinterface.receive()))
        msg2 = Status.from_json(json.dumps(webinterface.receive()))
        msg3 = Status.from_json(json.dumps(webinterface.receive()))

        expct1 = Status.ok({
            'script_status': 'waiting_for_slaves',
            'script_id': self.script.id,
        })
        expct2 = Status.ok({
            'message':
            "Send start command to client `{}`".format(self.prog1.slave.name),
        })
        expct3 = Status.ok({
            'message':
            "Send start command to client `{}`".format(self.prog2.slave.name),
        })

        self.assertStatusSet(
            [msg1, msg2, msg3],
            [expct1, expct2, expct3],
        )

    def test_state_next_offline(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.slave1.online = True
        self.slave1.save()

        self.sched._Scheduler__index = -1
        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            Status.ok({
                'program_status': 'started',
                'pid': self.prog1.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS,
        )

        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.ERROR,
        )

        self.assertStatusRegex(
            Status.err(SlaveOfflineError),
            Status.err(self.sched._Scheduler__error_code),
        )

    def test_state_next_finished(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.slave1.online = True
        self.slave1.save()
        self.slave2.online = True
        self.slave2.save()

        ProgramStatusModel.objects.create(program=self.prog1, code='0',
                                          command_uuid='0')

        self.sched._Scheduler__index = -1
        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()


        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS,
        )

        msg1 = Status.from_json(json.dumps(webinterface.receive()))

        expct1 = Status.ok({
            'script_status': 'next_step',
            'index': 0,
            'last_index': -1,
            'start_time': 0,
            'script_id': self.script.id,
        })

        self.assertStatusSet(
            [msg1],
            [expct1]
        )

        ProgramStatusModel.objects.create(program=self.prog2, code='0',
                                          command_uuid='1')

        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS,
        )

        msg1 = Status.from_json(json.dumps(webinterface.receive()))

        expct1 = Status.ok({
            'script_status': 'next_step',
            'index': 2,
            'last_index': 0,
            'start_time': 1,
            'script_id': self.script.id,
        })

        self.assertStatusSet(
            [msg1],
            [expct1]
        )

        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.SUCCESS,
        )

        self.assertEqual(
            Status.ok({
                'script_status': 'next_step',
                'index': -1,
                'last_index': 2,
                'start_time': 0,
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_state_next(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.slave1.online = True
        self.slave1.save()
        self.slave2.online = True
        self.slave2.save()

        self.sched._Scheduler__index = -1
        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()


        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS,
        )

        msg1 = Status.from_json(json.dumps(webinterface.receive()))
        msg2 = Status.from_json(json.dumps(webinterface.receive()))

        expct1 = Status.ok({
            'script_status': 'next_step',
            'index': 0,
            'last_index': -1,
            'start_time': 0,
            'script_id': self.script.id,
        })

        expct2 = Status.ok({
            'program_status': 'started',
            'pid': self.prog1.id,
        })

        self.assertStatusSet(
            [msg1, msg2],
            [expct1, expct2]
        )

        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS,
        )

        msg1 = Status.from_json(json.dumps(webinterface.receive()))
        msg2 = Status.from_json(json.dumps(webinterface.receive()))

        expct1 = Status.ok({
            'script_status': 'next_step',
            'index': 2,
            'last_index': 0,
            'start_time': 1,
            'script_id': self.script.id,
        })

        expct2 = Status.ok({
            'program_status': 'started',
            'pid': self.prog2.id,
        })

        self.assertStatusSet(
            [msg1, msg2],
            [expct1, expct2]
        )

        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.SUCCESS,
        )

        self.assertEqual(
            Status.ok({
                'script_status': 'next_step',
                'index': -1,
                'last_index': 2,
                'start_time': 0,
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_state_waiting_programs(self):
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__index = 0
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS

        ProgramStatusModel(
            running=True,
            program=self.prog1,
            command_uuid=uuid4().hex,
        ).save()
        ProgramStatusModel(
            running=False,
            program=self.prog2,
            command_uuid=uuid4().hex,
        ).save()

        self.sched._Scheduler__state_wait_programs_filesystems()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS,
        )

        ProgramStatusModel.objects.filter(program=self.prog1).update(
            running=False, )

        self.sched._Scheduler__state_wait_programs_filesystems()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.NEXT_STEP,
        )

        self.sched._Scheduler__index = 2
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS

        ProgramStatusModel.objects.filter(program=self.prog2).update(
            running=False, )

        self.sched._Scheduler__state_wait_programs_filesystems()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.NEXT_STEP,
        )


    def test_state_success(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.SUCCESS
        self.sched._Scheduler__state_success()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.SUCCESS,
        )

        self.assertEqual(
            Status.ok({
                'script_status': 'success',
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_state_error(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__error_code = "Wow an error occurred."
        self.sched._Scheduler__state = SchedulerStatus.ERROR
        self.sched._Scheduler__state_error()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.ERROR,
        )

        self.assertEqual(
            Status.ok({
                'script_status': 'error',
                'error_code': 'Wow an error occurred.',
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_timer_slave_timeout(self):
        from threading import Timer
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.sched._Scheduler__event = asyncio.Event(loop=self.sched.loop)
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_SLAVES

        t = Timer(
            1,
            self.sched.slave_timeout_callback,
        )

        t.start()
        t.join()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.ERROR,
        )

        self.assertEqual(
            self.sched._Scheduler__error_code,
            "Not all slaves connected within 5 minutes.",
        )
