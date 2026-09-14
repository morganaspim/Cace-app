import pytest
from cace_studio.modules.fem_v042 import deterministic_schedule,scheduler_fixture
from cace_studio.core.module import ValidationError
def test_v042_scheduler():
 r=scheduler_fixture(); assert r['schedule']==['assemble','order','factor','solve','verify']
 with pytest.raises(ValidationError): deterministic_schedule(['a','b'],{'a':['b'],'b':['a']})
