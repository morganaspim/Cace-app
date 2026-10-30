"""M.E.R.L.I.N. fail-closed research claim regression."""
import json
from pathlib import Path

def test_merlin_packet_does_not_inflate_scientific_claims():
    data=json.loads((Path(__file__).parent.parent/'MERLIN_EVIDENCE_PACKET.json').read_text())
    assert data['schema_version']==1
    assert all(value is False for value in data['claims'].values())
    assert data['sources']['research_commit']
    assert any(x['class']=='LEAN_KERNEL_CONDITIONAL' and x['status']=='PASS'
               for x in data['verification'])
    assert any(x['status']=='PASS' and x['class']=='NUMERICAL_HOSTED'
               for x in data['verification'])
    for item in data['verification']:
        assert item.get('limitation')
