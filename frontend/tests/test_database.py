#  pylint: disable=C0111,C0103,R0201

from django.test import TestCase
from django.core.exceptions import ValidationError

from frontend.apps import flush

from frontend.models import (
    Slave as SlaveModel,
    ProgramStatus as ProgramStatusModel,
    validate_mac_address,
    validate_argument_list,
)

from .factory import (
    SlaveFactory,
    ScriptFactory,
    FileFactory,
    ProgramFactory,
    ProgramStatusFactory,
    SGPFactory,
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

    def test_script_has_error(self):
        script = ScriptFactory()

        self.assertFalse(script.has_error)

        script.error_code = "oops"
        script.save()

        self.assertTrue(script.has_error)

    def test_script_indexes(self):
        script = ScriptFactory()
        slave = SlaveFactory()
        prog1 = ProgramFactory(slave=slave)
        prog2 = ProgramFactory(slave=slave)

        sgp1 = SGPFactory(index=0, program=prog1, script=script)
        sgp2 = SGPFactory(index=2, program=prog2, script=script)

        self.assertEqual([
            sgp1.index,
            sgp2.index,
        ], list(script.indexes))

    def test_script_name(self):
        script = ScriptFactory()
        self.assertEqual(script.name, str(script))

    def test_slave_has_err(self):
        slave = SlaveFactory()

        self.assertFalse(slave.has_error)
        self.assertFalse(slave.has_running)

    def test_slave_has_error_true(self):
        filesystem = FileFactory(error_code="Hey")

        self.assertTrue(filesystem.slave.has_error)

    def test_slave_is_online_err(self):
        slave = SlaveFactory()
        self.assertFalse(slave.is_online)

    def test_program_is_timeouted(self):
        status = ProgramStatusFactory(running=True, timeouted=True)
        prog = status.program
        slave = prog.slave

        self.assertTrue(slave.has_running)
        self.assertFalse(slave.has_error)
        self.assertTrue(prog.is_running)
        self.assertFalse(prog.is_executed)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_error)
        self.assertTrue(prog.is_timeouted)

    def test_program_is_err(self):
        prog = ProgramFactory()

        self.assertFalse(prog.is_running)
        self.assertFalse(prog.is_error)
        self.assertFalse(prog.is_successful)
        self.assertFalse(prog.is_executed)
        self.assertFalse(prog.is_timeouted)

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
        self.assertFalse(prog.is_timeouted)

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
        self.assertFalse(prog.is_timeouted)

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
        self.assertFalse(prog.is_timeouted)

    def test_flush_error(self):
        slave = SlaveFactory()

        flush('Slave')
        flush('UnknownModel')

        self.assertFalse(SlaveModel.objects.filter(name=slave.name).exists())

    def test_filesystem_state(self):
        moved = FileFactory(hash_value="Some")
        errored = FileFactory(error_code="Some")
        restored = FileFactory()

        self.assertEqual(moved.data_state, "moved")
        self.assertEqual(errored.data_state, "error")
        self.assertEqual(restored.data_state, "restored")

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

        ProgramStatusFactory(program=prog)

        self.assertEqual(ProgramStatusModel.objects.count(), 1)

        flush("ProgramStatus")

        self.assertEqual(ProgramStatusModel.objects.count(), 0)

    def test_filesystem_str(self):
        filesystem = FileFactory()
        self.assertEqual(
            str(filesystem),
            filesystem.name,
        )
