import math
import unittest
from cace_studio.ai.snapshot_broker import SnapshotBroker, BrokerError, tool_for_snapshot
from cace_studio.ai.investigation import Investigator, EngineeringSpec, PlanState, Outcome

class SnapshotBrokerTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'instrument': 'sensor-A', 'kind': 'rf', 'accepted': True, 'value': 1.25},
            {'instrument': 'sensor-B', 'kind': 'rf', 'accepted': False, 'value': 1.5},
            {'instrument': 'sensor-C', 'kind': 'optical', 'accepted': True, 'value': 4.0},
            {'instrument': 'sensor-D', 'kind': 'optical', 'accepted': True, 'value': 4.25},
        ]
        self.b = SnapshotBroker(
            {'experiments': self.rows},
            {'experiments': ('instrument','kind','accepted','value')},
            max_rows=32,
            max_output=10,
            min_group=2,
        )

    def test_select_returns_allowed_columns_and_copies(self):
        actual = self.b.select('experiments', ('instrument', 'value'), where={'kind': 'rf'})
        self.assertEqual(actual, [{'instrument': 'sensor-A', 'value': 1.25}, {'instrument': 'sensor-B', 'value': 1.5}])
        actual[0]['instrument']='changed'
        self.assertEqual(self.b.select('experiments', ('instrument',), where={'kind': 'rf'})[0]['instrument'], 'sensor-A')
        self.rows[0]['instrument']='changed-at-source'
        self.assertEqual(self.b.select('experiments', ('instrument',))[0]['instrument'], 'sensor-A')

    def test_count_and_suppressed_group_counts(self):
        self.assertEqual(self.b.count('experiments', where={'kind':'rf'}), 2)
        counts = self.b.group_count('experiments','kind')
        self.assertEqual(counts, {'optical': 2, 'rf': 2})
        self.assertEqual(self.b.group_count('experiments','accepted'), {True: 3})

    def test_unknown_fields_and_operations_fail_closed(self):
        for callback in (
            lambda: self.b.select('experiments', ('secret',)),
            lambda: self.b.select('unknown', ('instrument',)),
            lambda: self.b.count('experiments', where={'name':'z'}),
            lambda: self.b.select('experiments', ('instrument',), where={'kind': {'$or':['rf']}}),
            lambda: self.b.group_count('experiments', 'secret'),
            lambda: self.b.select('experiments', ('instrument',),limit=100),
            lambda: self.b.select('experiments', ('instrument',),where={'value': float('nan')}),
        ):
            with self.assertRaises(BrokerError): callback()

    def test_reject_dataset_schema_mismatch_and_unbounded_or_nested_data(self):
        with self.assertRaises(BrokerError):
            SnapshotBroker({'experiments': [{'value':1, 'password':'abc'}]}, {'experiments':('value',)})
        with self.assertRaises(BrokerError):
            SnapshotBroker({'x':[{'a':{'nested':'record'}}]}, {'x':('a',)})
        with self.assertRaises(BrokerError):
            SnapshotBroker({'x':[{'a':float('inf')}]}, {'x':('a',)})
        with self.assertRaises(BrokerError):
            SnapshotBroker({'x':[{'a':i} for i in range(11)]}, {'x':('a',)},max_rows=10)
        with self.assertRaises(BrokerError):
            SnapshotBroker({'../x':[{'a':1}]}, {'../x':('a',)})

    def test_no_query_language_or_python_callback_surface(self):
        self.assertFalse(hasattr(self.b, 'execute_code'))
        self.assertFalse(hasattr(self.b, 'run_python'))
        with self.assertRaises(BrokerError): self.b.select('experiments', ('__class__',))

    def test_filter_zero_matches_is_not_evidence_of_absence(self):
        self.assertEqual(self.b.count('experiments', where={'kind':'nonexistent'}), 0)
        self.assertEqual(self.b.group_count('experiments','kind',where={'instrument':'nonexistent'}), {})

    def test_validation_limits_and_empty_schema(self):
        with self.assertRaises(BrokerError):
            SnapshotBroker({'x': []}, {'x': ()})
        with self.assertRaises(BrokerError):
            SnapshotBroker({'x': [{'a':1}]}, {'x':('a',)}, max_output=0)
        with self.assertRaises(BrokerError):
            self.b.select('experiments', ())

    def test_broker_exposes_fixed_scope_agent_tool_with_required_permission(self):
        tool = tool_for_snapshot(self.b, dataset='experiments', operation='count',
                                 tool_id='sensor_count', capability='count_experiments')
        self.assertEqual(tool.required_permission, 'project_dataset_read')
        self.assertEqual(tool.handler({'where': {'kind':'rf'}}), 2)
        agent = Investigator()
        agent.register(tool)
        missing = EngineeringSpec('Count observations', 'signal', ('Check exact count',),
                                  permissions=('local_read',))
        plan = agent.plan(missing, ('count_experiments',))
        self.assertEqual(plan.state, PlanState.BLOCKED)
        authorized = EngineeringSpec('Count observations', 'signal', ('Check exact count',),
                                     permissions=('project_dataset_read',))
        plan = agent.plan(authorized, ('count_experiments',))
        self.assertEqual(plan.state, PlanState.READY)
        self.assertEqual(agent.execute(plan, {'where': {'kind':'optical'}}).outcome,
                         Outcome.COMPLETED_ADVISORY)

    def test_broker_tool_rejects_request_overrides_and_unknown_operations(self):
        with self.assertRaises(BrokerError):
            tool_for_snapshot(self.b, dataset='experiments', operation='shell',
                              tool_id='bad', capability='bad')
        tool = tool_for_snapshot(self.b, dataset='experiments', operation='select',
                                 fields=('instrument',), tool_id='read', capability='records')
        self.assertEqual(len(tool.handler({'where': {'kind':'rf'}})), 2)
        with self.assertRaises(BrokerError):
            tool.handler({'where': {}, 'operation': 'exec'})

if __name__=='__main__': unittest.main()
