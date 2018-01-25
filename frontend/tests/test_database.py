#  pylint: disable=C0111,C0103,R0201

from django.test import TestCase
from django.core.exceptions import ValidationError

from frontend.apps import flush

from frontend.models import (
    Slave as SlaveModel,
    SlaveStatus as SlaveStatusModel,
    ProgramStatus as ProgramStatusModel,
    validate_mac_address,
    validate_argument_list,
)

from .factory import (
    SlaveFactory,
    SlaveStatusFactory,
    ProgramFactory,
    ProgramStatusFactory,
)


class DatabaseTests(TestCase):  # pylint: disable=unused-variable
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
        slave = SlaveFactory()

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
        prog = ProgramFactory()

        self.assertFalse(prog.is_running)
        self.assertFalse(prog.is_error)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_executed)

    def test_program_running(self):
        status = ProgramStatusFactory(running=True)
        prog = status.program
        slave = prog.slave

        self.assertTrue(slave.has_running)
        self.assertFalse(slave.has_error)
        self.assertTrue(prog.is_running)
        self.assertFalse(prog.is_executed)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_error)

    def test_program_successful(self):
        status = ProgramStatusFactory(code="0")
        prog = status.program
        slave = prog.slave

        self.assertFalse(slave.has_running)
        self.assertFalse(slave.has_error)
        self.assertFalse(prog.is_running)
        self.assertTrue(prog.is_executed)
        self.assertTrue(prog.is_successful)
        self.assertFalse(prog.is_error)

    def test_program_error(self):
        status = ProgramStatusFactory(code="1")
        prog = status.program
        slave = prog.slave

        self.assertFalse(slave.has_running)
        self.assertTrue(slave.has_error)
        self.assertFalse(prog.is_running)
        self.assertTrue(prog.is_executed)
        self.assertFalse(prog.is_successful)
        self.assertTrue(prog.is_error)

    def test_flush_error(self):
        slave = SlaveFactory()

        flush('Slave')
        flush('UnknownModel')

        self.assertFalse(SlaveModel.objects.filter(name=slave.name).exists())

    def test_slave_insert_invalid_ip(self):
        self.assertRaises(
            ValidationError, SlaveModel(ip_address='my_cool_ip').full_clean)

    def test_slave_insert_invalid_mac(self):
        self.assertRaises(
            ValidationError, SlaveModel(mac_address='my_cool_mac').full_clean)

    def test_mac_validator_upper(self):
        validate_mac_address("00:AA:BB:CC:DD:EE")

    def test_mac_validator_lower(self):
        validate_mac_address("00:aa:bb:cc:dd:ee")

    def test_mac_validator_mixed(self):
        validate_mac_address("00:Aa:Bb:cC:dD:EE")

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
        slave = SlaveFactory()
        prog = ProgramFactory(slave=slave)

        SlaveStatusFactory(slave=slave)
        ProgramStatusFactory(program=prog)

        self.assertEqual(SlaveStatusModel.objects.count(), 1)
        self.assertEqual(ProgramStatusModel.objects.count(), 1)

        flush("SlaveStatus", "ProgramStatus")

        self.assertEqual(SlaveStatusModel.objects.count(), 0)
        self.assertEqual(ProgramStatusModel.objects.count(), 0)
