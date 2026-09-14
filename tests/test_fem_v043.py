from cace_studio.modules.fem_v043 import ordering_portfolio
def test_v043_portfolio():
 r=ordering_portfolio(); assert r['winner_by_fill'] in {x['ordering'] for x in r['rows']}; assert r['pareto_fill_front']
