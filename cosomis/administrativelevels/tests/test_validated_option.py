"""Every command reading CouchDB task documents reads only validated tasks by
default, and takes --validated to read others."""
from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase

from administrativelevels.management.commands._couch_sync import validated_condition

COMMANDS = (
    '2_syncpriorities', '3_syncpopulation', '4_syncendorsement', '5_synctasks', '7_updatetaskresponses',
    '8_syncclimatecontribution', '9_syncattachments', 'check_missing_investments', 'export_cdd_data',
    'priorities_diagnostic', 'update_investment_description',
)
NOT_YET_VALIDATED = [{'validated': None}, {'validated': {'$exists': False}}]
# Arguments a command needs to run unattended.
UNATTENDED = {'7_updatetaskresponses': ('--noinput',)}


class ValidatedConditionTests(SimpleTestCase):
    def test_each_combination(self):
        cases = {
            ('true',): {'validated': True},
            ('false',): {'validated': False},
            ('none',): {'$or': NOT_YET_VALIDATED},
            ('false', 'none'): {'$or': [{'validated': False}] + NOT_YET_VALIDATED},
            ('true', 'false'): {'validated': {'$in': [True, False]}},
            ('true', 'false', 'none'): None,
            ('all',): None,
        }
        for values, expected in cases.items():
            with self.subTest(values=values):
                self.assertEqual(validated_condition(values), expected)


class FakeCouch:
    """One valid facilitator database without any task; records the selectors."""

    def __init__(self):
        self.selectors = []

    def list_all_databases(self, prefix=None):
        return ['facilitator_1']

    def get_db(self, name):
        return self

    def get_query_result(self, selector, fields=None, **kwargs):
        if selector == {'type': 'facilitator'}:
            return [{'develop_mode': False, 'training_mode': False}]
        self.selectors.append(selector)
        return []


def _dicts(node):
    if isinstance(node, dict):
        yield node
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return
    for child in children:
        yield from _dicts(child)


class CommandsValidatedOptionTests(TestCase):
    def _selectors(self, command, *args):
        couch = FakeCouch()
        module = import_module('administrativelevels.management.commands.' + command)
        # export_cdd_data writes its export next to manage.py.
        with mock.patch.object(module, 'NoSQLClient', return_value=couch), \
                mock.patch.object(module, 'open', mock.mock_open(), create=True), \
                redirect_stdout(StringIO()):
            call_command(command, *args, *UNATTENDED.get(command, ()), stdout=StringIO(), stderr=StringIO())
        self.assertTrue(couch.selectors, '%s sent no task query' % command)
        return [node for selector in couch.selectors for node in _dicts(selector)]

    def test_only_validated_tasks_are_read_by_default(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assertIn({'validated': True}, self._selectors(command))

    def test_other_tasks_are_read_on_request(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                nodes = self._selectors(command, '--validated', 'false', 'none')
                self.assertIn({'$or': [{'validated': False}] + NOT_YET_VALIDATED}, nodes)
                self.assertNotIn({'validated': True}, nodes)

    def test_all_reads_every_task(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                nodes = self._selectors(command, '--validated', 'all')
                self.assertFalse([node for node in nodes if 'validated' in node])

    def test_planning_cycle_filters_tasks_but_not_phases_or_activities(self):
        couch = FakeCouch()
        module = import_module('administrativelevels.management.commands.5_synctasks')
        with mock.patch.object(module, 'NoSQLClient', return_value=couch):
            call_command('5_synctasks', stdout=StringIO(), stderr=StringIO())

        self.assertEqual(couch.selectors, [{'$or': [
            {'type': {'$in': ['phase', 'activity']}},
            {'$and': [{'type': 'task'}, {'validated': True}]},
        ]}])

    def test_unknown_value_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command('5_synctasks', '--validated', 'yes', stdout=StringIO(), stderr=StringIO())


class UpdateTaskResponsesConfirmationTests(SimpleTestCase):
    """7_updatetaskresponses rewrites form_responses in a format the task modal
    cannot display, so it asks before touching anything."""

    def _run(self, *args, answer=None):
        module = import_module('administrativelevels.management.commands.7_updatetaskresponses')
        out = StringIO()
        with mock.patch.object(module, 'NoSQLClient', return_value=FakeCouch()) as client, \
                mock.patch.object(module, 'input', create=True, side_effect=answer) as prompt:
            call_command('7_updatetaskresponses', *args, stdout=out, stderr=StringIO())
        return client, prompt, out.getvalue()

    def test_anything_but_yes_cancels_before_reading_couchdb(self):
        for answer in ('no', '', 'oui'):
            with self.subTest(answer=answer):
                client, prompt, out = self._run(answer=[answer])

                prompt.assert_called_once()
                client.assert_not_called()
                self.assertIn('Annulé', out)

    def test_yes_continues(self):
        client, _, _ = self._run(answer=['yes'])

        client.assert_called_once()

    def test_without_a_terminal_it_cancels(self):
        client, _, _ = self._run(answer=EOFError)

        client.assert_not_called()

    def test_noinput_continues_without_asking(self):
        client, prompt, _ = self._run('--noinput')

        prompt.assert_not_called()
        client.assert_called_once()
