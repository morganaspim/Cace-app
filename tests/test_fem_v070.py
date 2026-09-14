from cace_studio.modules.fem_v070 import normalized_benchmark
def test_v070():
 r=normalized_benchmark(); assert r['pass'] and r['median_seconds']==0.01 and r['throughput']==100000.0
