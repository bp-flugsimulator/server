#  pylint: disable=C0111
#  pylint: disable=C0103

from uuid import uuid4
from datetime import datetime

from django.test import TestCase
from django.core.exceptions import ValidationError

from frontend.models import (
    Slave as SlaveModel,
    SlaveStatus as SlaveStatusModel,
    Program as ProgramModel,
    ProgramStatus as ProgramStatusModel,
    validate_mac_address,
    validate_argument_list,
)

class DatabaseTests(TestCase): # pylint: diasble=unused-variable
    def test_validate_argument_list(self):
        self.assertIsNone(validate_argument_list('a b c d e f g'))

    def test_validate_argument_list_raises(self):
        self.assertRaisesMessage(
            ValidationError,
            'Enter a valid argument list.',
            validate_argument_list,
            'a "abc',
)

    def test_slave_has_err(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="192.168.5.0",
            mac_address="00:02:00:00:00:00",
        )

        slave.save()

        prog = ProgramModel(slave=slave, name="test_prog", path="None")
        prog.save()

        self.assertFalse(slave.has_error)
        self.assertFalse(slave.has_running)

    def test_slave_is_online_err(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="192.168.5.0",
            mac_address="00:02:00:00:00:00",
        )

        slave.save()

        self.assertFalse(slave.is_online)

    def test_program_is_err(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="192.168.5.0",
            mac_address="00:02:00:00:00:00",
        )

        slave.save()

        prog = ProgramModel(slave=slave, name="test_prog", path="None")
        prog.save()

        self.assertFalse(prog.is_running)
        self.assertFalse(prog.is_error)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_executed)

    def test_slave_insert_valid(self):
        mod = SlaveModel(
            name="Tommo3",
            ip_address="192.168.5.39",
            mac_address="00:02:00:00:00:00",
        )
        mod.full_clean()
        mod.save()
        self.assertTrue(SlaveModel.objects.filter(name="Tommo3").exists())

    def test_program_running(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.2.0",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(name="test_program", path="none", slave=slave)
        prog.save()

        ProgramStatusModel(
            command_uuid=uuid4(),
            code="",
            program=prog,
            running=True,
        ).save()

        self.assertTrue(slave.has_running)
        self.assertFalse(slave.has_error)
        self.assertTrue(prog.is_running)
        self.assertFalse(prog.is_executed)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_error)

    def test_program_successful(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.2.0",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(name="test_program", path="none", slave=slave)
        prog.save()

        ProgramStatusModel(
            command_uuid=uuid4(),
            code="0",
            program=prog,
            running=False,
        ).save()

        self.assertFalse(slave.has_running)
        self.assertFalse(slave.has_error)
        self.assertFalse(prog.is_running)
        self.assertTrue(prog.is_executed)
        self.assertTrue(prog.is_successful)
        self.assertFalse(prog.is_error)

    def test_program_error(self):
        slave = SlaveModel(
            name="test_slave",
            ip_address="0.0.2.0",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(name="test_program", path="none", slave=slave)
        prog.save()

        ProgramStatusModel(
            command_uuid=uuid4(),
            code="1",
            program=prog,
            running=False,
        ).save()

        self.assertFalse(slave.has_running)
        self.assertTrue(slave.has_error)
        self.assertFalse(prog.is_running)
        self.assertTrue(prog.is_executed)
        self.assertFalse(prog.is_successful)
        self.assertTrue(prog.is_error)

    def test_flush_error(self):
        from frontend.apps import flush
        SlaveModel(
            name='test_flush_error',
            ip_address='0.1.0.0',
            mac_address='00:01:00:00:00:00',
        ).save()
        flush('Slave')
        flush('UnknownModel')
        self.assertFalse(
            SlaveModel.objects.filter(name='test_flush_error').exists())

    def test_slave_insert_invalid_ip(self):
        self.assertRaises(
            ValidationError, SlaveModel(ip_address='my_cool_ip').full_clean)

    def test_slave_insert_invalid_mac(self):
        self.assertRaises(
            ValidationError, SlaveModel(mac_address='my_cool_mac').full_clean)

    def test_mac_validator_upper(self):
        validate_mac_address("00:AA:BB:CC:DD:EE")
        self.assertTrue(True)

    def test_mac_validator_lower(self):
        validate_mac_address("00:aa:bb:cc:dd:ee")
        self.assertTrue(True)

    def test_mac_validator_mixed(self):
        validate_mac_address("00:Aa:Bb:cC:dD:EE")
        self.assertTrue(True)

    def test_mac_validator_too_short(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23",
        )

    def test_mac_validator_too_long(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23:23:23:23:32",
        )

    def test_mac_validator_too_long_inner(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23:223:23:23",
        )

    def test_mac_validator_too_short_inner(self):
        self.assertRaises(
            ValidationError,
            validate_mac_address,
            "00:02:23:2:23:23",
        )

    def test_flush(self):
        slave = SlaveModel(
            name="test",
            ip_address="127.0.0.1",
            mac_address="00:00:00:00:00:00",
        )
        slave.save()

        prog = ProgramModel(
            name="test",
            path="None",
            arguments="None",
            slave=slave,
        )
        prog.save()

        status_slave = SlaveStatusModel(slave=slave, command_uuid='abc')
        status_slave.save()

        status_program = ProgramStatusModel(prog.id, "None", datetime.now())
        status_program.save()

        self.assertEqual(SlaveStatusModel.objects.count(), 1)
        self.assertEqual(ProgramStatusModel.objects.count(), 1)

        from frontend.apps import flush
        flush("SlaveStatus", "ProgramStatus")

        self.assertEqual(SlaveStatusModel.objects.count(), 0)
        self.assertEqual(ProgramStatusModel.objects.count(), 0)
