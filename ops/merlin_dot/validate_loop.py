"""Exact overlay on retained recovery controller; no deployment or new grants."""
import base64
import hashlib
import json

SOURCE = '47874bc1ded7b59b167c0052564e8d6ff31daae2'
PARENT_CONTROLLER = 'a35e5c3fe0126011d5c5d10080e5c297ca5965b7'
PINS = {
    'python/merlin/hermes_systemd.py': '9a001e7d062cb7f884940cfd126af3863be0ed0e',
    'python/merlin/build_loop.py': '05676a366782574735cff01fda1ac273d1381627',
    'tests/test_build_loop.py': '96d76d3621dfc8a7aff6339be6b3d3fdbd57d719',
}
MANAGER_TEST = '''
class ManagerStreamTests(unittest.TestCase):
    def test_manager_opens_streams_without_passing_file_descriptors(self):
        from merlin.hermes_systemd import _command
        properties=_properties(ProcessLimits(),8)
        properties.update(StandardInput='file:/run/fixed/stdin',StandardOutput='file:/run/fixed/stdout',StandardError='file:/run/fixed/stderr')
        args=_command('merlin-fixed-fixture.service',properties,{'unit':'merlin-fixed-fixture.service'})
        self.assertNotIn('--pipe',args)
        for stream in ('Input','Output','Error'):
            self.assertTrue(any(x.startswith('--property=Standard'+stream+'=file:/run/') for x in args))
        self.assertIn('--property=NoNewPrivileges=yes',args)
        self.assertIn('--property=KillMode=control-group',args)
        self.assertIn('--property=PrivateNetwork=yes',args)
'''


def git(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def blob(api, identity):
    obj=api('git/blobs/'+identity)
    if obj.get('sha')!=identity or obj.get('encoding')!='base64' or type(obj.get('size')) is not int or not 0<=obj['size']<=32000:
        raise ValueError('fixed bounded blob required')
    raw=base64.b64decode(''.join(obj['content'].split()),validate=True)
    if len(raw)!=obj['size'] or git(raw)!=identity:
        raise ValueError('blob bytes differ')
    return raw


def replace_once(text, before, after):
    if text.count(before)!=1:
        raise ValueError('controller transform preimage differs')
    return text.replace(before,after)


def run(api, output):
    replacements={name:blob(api,identity) for name,identity in PINS.items()}
    parent=blob(api,PARENT_CONTROLLER).decode('utf-8')
    old='8fbf73d563745aea28f227f14fec9fa78d5c03a46bc0a4889cacbf333a211cf0'
    new=hashlib.sha256(replacements['python/merlin/hermes_systemd.py']).hexdigest()
    if parent.count(old)!=2:
        raise ValueError('privileged module pin count differs')
    source=parent.replace(old,new)
    source=replace_once(source,'r.testsRun==281','r.testsRun==302')
    source=replace_once(source,"        report['source_map_sha256']=final_map", "        files=overlay(files)\n        final_map=sha(json.dumps({n:sha(b) for n,b in sorted(files.items())},sort_keys=True,separators=(',',':')).encode())\n        report['source_commit']='"+SOURCE+"'\n        report['source_map_sha256']=final_map")
    source=replace_once(source,"manifest={'schema':'merlin-recovery-source/1','parent_source_commit':PARENT,", "manifest={'schema':'merlin-recovery-source/1','source_commit':'"+SOURCE+"','parent_source_commit':PARENT,")
    def overlay(files):
        result=dict(files)
        result.update(replacements)
        name='tests/test_hermes_systemd.py'
        result[name]=result[name]+MANAGER_TEST.encode()
        if git(result[name])!='29d87f88c6baebf8740ee0803fe6f5696f55dc54' or len(result)!=111:
            raise ValueError('overlay scope or test identity differs')
        return result
    receipt={'schema':'merlin-loop-controller/1','source_commit':SOURCE,'parent_controller':PARENT_CONTROLLER,
             'overlay_git_blobs':PINS,'transformed_controller_sha256':hashlib.sha256(source.encode()).hexdigest(),
             'expected_tests':302,'expected_kernel_cases':8,'qualification':False,'promotion_authority':False}
    (output/'loop-controller.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    namespace={'overlay':overlay}
    exec(compile(source,'exact-transformed-recovery-controller','exec'),namespace)
    return namespace['run'](api,output)
