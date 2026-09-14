from cace_studio.modules.fem_v048 import budget_fixture,evaluate_regression
def test_v048_budget():
 assert budget_fixture()['all_pass']; assert not evaluate_regression(12,10,.1)['pass']
