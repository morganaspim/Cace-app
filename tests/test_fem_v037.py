from cace_studio.modules.fem_v037 import certificate_fixture,validate_certificate_schema
def test_v037_schema():
 r=certificate_fixture(); assert r['validation']['valid']; bad=dict(r['certificate']); bad.pop('status'); assert not validate_certificate_schema(bad)['valid']
