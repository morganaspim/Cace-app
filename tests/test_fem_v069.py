from cace_studio.modules.fem_v069 import evidence_lattice
def test_v069():
 r=evidence_lattice(); assert r['pass'] and r['formal_interval_incomparable']
