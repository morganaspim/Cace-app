from cace_studio.modules.fem_v022 import arena_plan, v022_memory_audit

def test_arena_alignment():
    p=arena_plan([1,3,5],64); assert p['blocks']==3; assert all(o%64==0 for o in p['offsets']); assert p['reserved_bytes']>0

def test_runtime_workspace_reuse_ratio():
    a=v022_memory_audit(7,7,2,1); assert 0<=a['reuse_ratio']<=1; assert a['runtime_workspace_upper_bytes']>0
