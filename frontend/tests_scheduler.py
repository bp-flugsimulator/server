"""
Test file for scheduler.py
"""
import json
from unittest import TestCase
from uuid import uuid4
from utils import Status

from channels.test import WSClient

from .models import (
    Slave as SlaveModel,
    validate_argument_list,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
    ScriptGraphPrograms as SGP,
    ScriptGraphFiles as SGF,
    Script as ScriptModel,
    File as FileModel,
)

from .scheduler import Scheduler, SchedulerStatus


class SchedulerTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super(SchedulerTests, cls).setUpClass()

        # clear all connections
        from django import db
        db.connections.close_all()

        script = ScriptModel(name="t1")
        script.save()

        slave1 = SlaveModel(
            name="test_slav21",
            ip_address="0.1.2.0",
            mac_address="01:01:01:00:00100",
        )
        slave1.save()

        slave2 = SlaveModel(
            name="test_sl1ve2",
            ip_address="0.1.2.1",
            mac_address="00:02:01:01:00:00",
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

        cls.sched = Scheduler()
        cls.script = script
        cls.slave1 = slave1
        cls.slave2 = slave2
        cls.prog1 = prog1
        cls.prog2 = prog2

    @classmethod
    def tearDownClass(cls):
        cls.sched.stop()
        cls.script.delete()
        cls.slave1.delete()
        cls.slave2.delete()

    def test_start(self):
        self.assertTrue(self.sched.start(self.script.id))
        self.assertTrue(self.sched.is_running())
        self.assertFalse(self.sched.start(self.script.id))
        self.assertFalse(self.sched.should_stop())
        self.sched.stop()
        self.assertTrue(self.sched.should_stop())

    def test_state_init(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.INIT
        self.sched._Scheduler__state_init()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_SLAVES,
        )

        self.assertEqual(
            Status.ok({
                'script_status': 'waiting_for_slaves',
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_state_waiting_slaves(self):
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_SLAVES
        self.sched._Scheduler__state_wait_slaves()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_SLAVES,
        )

        SlaveModel.objects.filter(id=self.slave1.id).update(
            online=True,
            command_uuid=uuid4().hex,
        )

        self.sched._Scheduler__state_wait_slaves()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_SLAVES,
        )

        SlaveModel.objects.filter(id=self.slave2.id).update(
            online=True,
            command_uuid=uuid4().hex,
        )

        self.sched._Scheduler__state_wait_slaves()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.NEXT_STEP,
        )

    def test_state_next(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

        self.sched._Scheduler__index = -1
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS,
        )

        self.assertEqual(
            Status.ok({
                'script_status': 'next_step',
                'index': 0,
                'last_index': -1,
                'start_time': 0,
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

        self.sched._Scheduler__state = SchedulerStatus.NEXT_STEP
        self.sched._Scheduler__state_next()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS,
        )

        self.assertEqual(
            Status.ok({
                'script_status': 'next_step',
                'index': 2,
                'last_index': 0,
                'start_time': 1,
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
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
                'index': 3,
                'last_index': 2,
                'start_time': 0,
                'script_id': self.script.id,
            }),
            Status.from_json(json.dumps(webinterface.receive())),
        )

    def test_state_waiting_programs(self):
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__index = 0
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_PROGRAMS

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

        self.sched._Scheduler__state_wait_programs()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS,
        )

        ProgramStatusModel.objects.filter(program=self.prog1).update(
            running=False, )

        self.sched._Scheduler__state_wait_programs()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.NEXT_STEP,
        )

        self.sched._Scheduler__index = 2
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_PROGRAMS

        ProgramStatusModel.objects.filter(program=self.prog2).update(
            running=False, )

        self.sched._Scheduler__state_wait_programs()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.NEXT_STEP,
        )

    def test_state_waiting_programs_error(self):
        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__index = 0
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_PROGRAMS

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

        self.sched._Scheduler__state_wait_programs()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.WAITING_FOR_PROGRAMS,
        )

        ProgramStatusModel.objects.filter(program=self.prog1).update(
            running=False, )

        self.sched._Scheduler__state_wait_programs()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.NEXT_STEP,
        )

        self.sched._Scheduler__index = 2
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_PROGRAMS

        ProgramStatusModel.objects.filter(program=self.prog2).update(
            running=False,
            code="Some error",
        )

        self.sched._Scheduler__state_wait_programs()

        self.assertEqual(
            self.sched._Scheduler__state,
            SchedulerStatus.ERROR,
        )

    def test_state_success(self):
        webinterface = WSClient()
        webinterface.join_group('notifications')

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

        self.sched._Scheduler__script = self.script.id
        self.sched._Scheduler__state = SchedulerStatus.WAITING_FOR_SLAVES

        t = Timer(
            1,
            self.sched.timer_scheduler_slave_timeout,
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
