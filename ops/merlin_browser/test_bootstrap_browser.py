"""Focused offline controls for package, archive and privilege boundaries."""
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

import bootstrap_browser as bootstrap
import launch_episode as launcher


def package(name):
    filename=name+'-'+bootstrap.CHROMIUM_VERSION+'-'+bootstrap.CHROMIUM_RELEASE+'.aarch64.rpm'
    return {'name':name,'epoch':'0','version':bootstrap.CHROMIUM_VERSION,'release':bootstrap.CHROMIUM_RELEASE,
      'arch':'aarch64','repository':'merlin-ol9-epel','url':bootstrap.REPOS['merlin-ol9-epel']+'getPackage/'+filename,
      'filename':filename,'sha256':'a'*64,'bytes':1024,'install_bytes':2048,'requires':[]}


class FixedBootstrapControls(unittest.TestCase):
    def setUp(self):
        self.packages=[package(name) for name in bootstrap.ROOT_PACKAGES]
        self.before=[{'name':'python3','epoch':'0','version':'3.9.25','release':'1.el9','arch':'aarch64'}]

    def test_exact_additive_plan_is_accepted(self):
        self.assertEqual(bootstrap.validate_transaction(self.packages,self.before,[])['upgrades'],0)

    def test_removal_is_rejected(self):
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_transaction(self.packages,self.before,['python3'])

    def test_existing_package_replacement_is_rejected(self):
        before=self.before+[dict((key,self.packages[0][key]) for key in ('name','epoch','version','release','arch'))]
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_transaction(self.packages,before,[])

    def test_wrong_root_version_is_rejected(self):
        self.packages[0]['version']='155.0'
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_transaction(self.packages,self.before,[])

    def test_cross_origin_dependency_is_rejected(self):
        self.packages[0]['url']='https://example.net/'+self.packages[0]['filename']
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_transaction(self.packages,self.before,[])

    def test_observed_rpm_snapshot_caret_filename_is_accepted(self):
        # Exact filename and content identity from candidate-plan.json in
        # native diagnostic run44934058026; no package bytes are installed.
        filename='aribb24-1.0.3^20160216git5e9be27-1.el9.aarch64.rpm'
        observed={'name':'aribb24','epoch':'0','version':'1.0.3^20160216git5e9be27','release':'1.el9',
          'arch':'aarch64','repository':'merlin-ol9-epel','filename':filename,
          'url':bootstrap.REPOS['merlin-ol9-epel']+'getPackage/'+filename,
          'sha256':'095d686374bef68af175b1b07db1bb3473d414b5e1262c9c6fa99f82cf34b5d5',
          'bytes':40987,'install_bytes':142054,'requires':[]}
        bounds=bootstrap.validate_transaction(self.packages+[observed],self.before,[])
        self.assertEqual(bounds['new_packages'],3)
        with self.assertRaisesRegex(bootstrap.BootstrapError,'source prefix'):
            bootstrap.validate_transaction(self.packages+[{**observed,'url':'https://foreign.example/'+filename}],self.before,[])

    def test_snapshot_filename_admission_still_rejects_paths_and_delimiters(self):
        for filename in ('../snapshot^1.rpm','dir/snapshot^1.rpm','dir\\snapshot^1.rpm',
                         'snapshot%2f^1.rpm','snapshot^1?.rpm','snapshot^1#.rpm',
                         'snapshot^1 .rpm','snapshot^1\n.rpm','snapshot^1;.rpm',
                         'snapshot$(id)^1.rpm','snapshot^1\x00.rpm'):
            values=copy.deepcopy(self.packages);values[0]['filename']=filename
            values[0]['url']=bootstrap.REPOS['merlin-ol9-epel']+'getPackage/'+filename
            with self.subTest(filename=filename):
                with self.assertRaisesRegex(bootstrap.BootstrapError,'filename'):
                    bootstrap.validate_transaction(values,self.before,[])

    def test_rejected_transaction_preserves_unvalidated_candidate(self):
        self.packages[0]['url']='https://different.example/'+self.packages[0]['filename']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaisesRegex(bootstrap.BootstrapError,'package source prefix differs'):
                bootstrap.checked_transaction(root,self.packages,self.before,[],{'effective_mirrors':['https://different.example/']})
            candidate=json.loads((root/'candidate-plan.json').read_text())
            rejection=json.loads((root/'candidate-rejection.json').read_text())
            self.assertFalse(candidate['validated']);self.assertEqual(candidate['packages'],self.packages)
            self.assertEqual(candidate['resolution_diagnostics']['effective_mirrors'],['https://different.example/'])
            self.assertEqual(rejection['candidate_sha256'],hashlib.sha256((root/'candidate-plan.json').read_bytes()).hexdigest())
            self.assertIn(self.packages[0]['url'],rejection['message'])

    def test_source_metadata_and_derived_cache_have_separate_finite_caps(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory);source=stage/'cache'/'repo'/'repodata';source.mkdir(parents=True)
            (source/'primary.xml.gz').write_bytes(b'x');(stage/'cache'/'repo.solv').write_bytes(b'x')
            def fake_identity(path,maximum):
                return {'sha256':'a'*64,'bytes':18 if 'repodata' in path.parts else 9}
            with mock.patch.object(bootstrap,'MAX_METADATA_SOURCE',20),mock.patch.object(bootstrap,'MAX_DERIVED_CACHE',10),mock.patch.object(bootstrap,'identity',side_effect=fake_identity):
                observed=bootstrap.metadata_identities(stage)
                self.assertEqual(observed['bytes_by_category'],{'repository_source':18,'derived_solver_cache':9})
                self.assertEqual(observed['overall_ceiling_bytes'],30)
                with mock.patch.object(bootstrap,'MAX_METADATA_SOURCE',17):
                    with self.assertRaisesRegex(bootstrap.BootstrapError,'repository_source'): bootstrap.metadata_identities(stage)
                with mock.patch.object(bootstrap,'MAX_DERIVED_CACHE',8):
                    with self.assertRaisesRegex(bootstrap.BootstrapError,'derived_solver_cache'): bootstrap.metadata_identities(stage)

    def test_arch_and_install_ceiling_are_strict(self):
        for field,value in (('arch','x86_64'),('install_bytes',bootstrap.MAX_INSTALLED+1),('bytes',True)):
            values=copy.deepcopy(self.packages);values[0][field]=value
            with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_transaction(values,self.before,[])

    def test_extra_packages_and_duplicate_names_are_bounded(self):
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_transaction(self.packages*33,self.before,[])
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_transaction(self.packages+[self.packages[0]],self.before,[])

    def test_fixed_wheel_python39_contract(self):
        self.assertEqual({p['name']:p['version'] for p in bootstrap.WHEELS},
                         {'playwright':'1.60.0','greenlet':'3.2.4','pyee':'13.0.0','typing-extensions':'4.14.1'})
        self.assertTrue(any('cp39-cp39' in p['filename'] for p in bootstrap.WHEELS))
        self.assertTrue(all(len(p['sha256'])==64 for p in bootstrap.WHEELS))

    def test_standard_public_key_fingerprint_parser(self):
        body=b'\x04'+b'\x00'*8
        packet=b'\x99'+len(body).to_bytes(2,'big')+body
        armor=b'-----BEGIN PGP PUBLIC KEY BLOCK-----\n'+base64.b64encode(packet)+b'\n-----END PGP PUBLIC KEY BLOCK-----\n'
        self.assertEqual(bootstrap.fingerprints(armor),[hashlib.sha1(packet).hexdigest().upper()])

    def test_secret_key_packets_are_never_accepted(self):
        packet=b'\x95\x01\x04'
        armor=b'-----BEGIN PGP PUBLIC KEY BLOCK-----\n'+base64.b64encode(packet)+b'\n-----END PGP PUBLIC KEY BLOCK-----\n'
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.fingerprints(armor)

    def test_duplicates_and_partial_key_packets_are_rejected(self):
        for raw in (b'\xc6\xe0\x04',b'\x9b\x04'):
            armor=b'-----BEGIN PGP PUBLIC KEY BLOCK-----\n'+base64.b64encode(raw)+b'\n-----END PGP PUBLIC KEY BLOCK-----\n'
            with self.assertRaises(bootstrap.BootstrapError): bootstrap.fingerprints(armor)

    def test_regular_input_never_opens_fifo_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fifo';os.mkfifo(path)
            with self.assertRaises(bootstrap.BootstrapError): bootstrap.regular(path,100)
            with self.assertRaises(launcher.LaunchError): launcher.read(path,100,root=False)

    def test_regular_input_rejects_leaf_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'real').write_bytes(b'value');(root/'link').symlink_to(root/'real')
            with self.assertRaises(OSError): bootstrap.regular(root/'link',100)
            with self.assertRaises(OSError): launcher.read(root/'link',100,root=False)

    def test_export_rejects_directory_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir();(source/'escape').symlink_to(root,target_is_directory=True)
            with self.assertRaises(launcher.LaunchError): launcher.export_tree(source,root/'result',100)

    def test_export_enforces_whole_tree_ceiling(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir();(source/'one').write_bytes(b'123456');(source/'two').write_bytes(b'123456')
            with self.assertRaises(launcher.LaunchError): launcher.export_tree(source,root/'result',10)

    def test_safe_episode_and_limits_are_not_command_inputs(self):
        for value in ('../x','--unit=x','x/y','a'*81,'a;id'):
            with self.assertRaises(launcher.LaunchError): launcher.safe_id(value)
        self.assertEqual(launcher.safe_id('native-evidence_01'),'native-evidence_01')
        self.assertEqual(launcher.validate_limits(launcher.CEILINGS.copy()),launcher.CEILINGS)
        for field in launcher.CEILINGS:
            limits=launcher.CEILINGS.copy();limits[field]=launcher.CEILINGS[field]+1
            with self.assertRaises(launcher.LaunchError): launcher.validate_limits(limits)

    def test_worker_namespaces_and_resource_clamps(self):
        config={'browser_uid':980,'browser_gid':980,'executable':'/usr/lib64/chromium-browser/headless_shell'}
        renderer=launcher.unit_command('merlin-browser-renderer-test.service',config,Path('/run/example'),Path('/opt/release'),'renderer',45)
        broker=launcher.unit_command('merlin-browser-broker-test.service',config,Path('/run/example'),Path('/opt/release'),'broker',45)
        self.assertIn('--property=PrivateNetwork=yes',renderer);self.assertIn('--property=PrivateNetwork=no',broker)
        for value in ('--property=NoNewPrivileges=yes','--property=CapabilityBoundingSet=',
                      '--property=KillMode=control-group','--property=RuntimeMaxSec=45','--property=MemorySwapMax=0'):
            self.assertIn(value,renderer);self.assertIn(value,broker)
        self.assertIn('--property=MemoryMax=1G',renderer);self.assertIn('--property=MemoryMax=128M',broker)
        self.assertNotIn('--no-sandbox',renderer);self.assertIn('--unshare-user',renderer)
        self.assertNotIn('/etc/pki',broker);self.assertNotIn('/var/lib/merlin-public-browser/registry',renderer)

    def test_supervisor_preserves_host_mount_visibility(self):
        unit=bootstrap.service_unit(Path('/opt/merlin-public-browser/releases/'+'a'*64)).decode()
        self.assertIn('ProtectHome=no',unit);self.assertIn('PrivateTmp=no',unit)
        self.assertIn('RestrictAddressFamilies=AF_UNIX',unit)
        self.assertNotIn('PrivateNetwork=yes',unit)
        self.assertIn('RuntimeDirectoryMode=0755',unit)
        self.assertEqual(bootstrap.duration_us('15min 30s'),930000000)
        self.assertEqual(bootstrap.duration_us('250ms'),250000)
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.duration_us('infinity')

    def test_actual_service_umask_cannot_hide_worker_input(self):
        with tempfile.TemporaryDirectory() as directory:
            run=Path(directory)/'episode';old=os.umask(0o077)
            try:
                launcher.prepare_run_tree(run)
                self.assertEqual(run.stat().st_mode&0o777,0o755)
                self.assertEqual((run/'input').stat().st_mode&0o777,0o755)
                self.assertEqual((run/'scratch').stat().st_mode&0o777,0o700)
            finally: os.umask(old)

    def test_request_cannot_choose_operation_or_package(self):
        request={'schema':'merlin-browser-bootstrap-request/1','request_id':'72efac38-891b-449e-b538-fd09dd2319c6',
                 'operation':bootstrap.CONTINUATION_OPERATION,'created_at':'2026-11-21T00:00:00Z'}
        execution={'runner':'cace-oci-a1','run_id':1,'run_attempt':1,'workflow_commit':'a'*40}
        bootstrap.validate_request(request,execution)
        for extra in ('command','url','packages','budget'):
            with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_request({**request,extra:'value'},execution)
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_request(request,{**execution,'run_attempt':2})
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_request({**request,'operation':'bootstrap'},execution)
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_request({**request,'request_id':bootstrap.PREDECESSOR['request_id']},execution)

    def inspected_payload(self):
        package={key:bootstrap.ZVBI[key] for key in ('name','epoch','version','release','arch','filename','bytes','sha256')}
        files=b'/usr/lib64/libzvbi.so.0.13.2\n/usr/lib/systemd/system/zvbid.service\n/usr/sbin/zvbid\n'
        scripts=b'fixed systemd helper postinstall only';xml=b'fixed complete inspected header'
        pin={**bootstrap.ZVBI,'files_sha256':bootstrap.digest(files),
             'scripts_sha256':bootstrap.digest(scripts),'xml_sha256':bootstrap.digest(xml)}
        return package,files,scripts,xml,pin

    def test_exact_inspected_payload_has_two_exclusions_and_no_blanket_suppression(self):
        package,files,scripts,xml,pin=self.inspected_payload()
        with mock.patch.object(bootstrap,'ZVBI',pin):
            observed=bootstrap.payload_policy(package,files,scripts,b'',xml)
        self.assertEqual(observed['excluded_paths'],list(pin['excluded_paths']))
        self.assertIn('--nopost',observed['scriptlet_policy'])
        self.assertIn('triggers retained',observed['scriptlet_policy'])

    def test_different_signed_package_does_not_inherit_zvbi_exception(self):
        package,files,scripts,xml,pin=self.inspected_payload()
        with mock.patch.object(bootstrap,'ZVBI',pin):
            for change in ({'sha256':'f'*64},{'filename':'zvbi-other.rpm'},{'name':'different'}):
                with self.subTest(change=change),self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.payload_policy({**package,**change},files,scripts,b'',xml)

    def test_new_script_or_trigger_or_privileged_payload_remains_rejected(self):
        package,files,scripts,xml,pin=self.inspected_payload()
        with mock.patch.object(bootstrap,'ZVBI',pin):
            for values in ((files,scripts+b' changed',b'',xml),(files,scripts,b'new trigger',xml),
                           (files,scripts,b'',xml+b'changed'),(files+b'/etc/cron.d/unrelated\n',scripts,b'',xml)):
                with self.subTest(values=values),self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.payload_policy(package,*values)

    def test_only_exact_one_package_stage_suppresses_postinstall(self):
        selected={key:bootstrap.ZVBI[key] for key in ('name','filename','bytes','sha256')}
        packages=[selected]+[{'name':'dependency-'+str(i),'filename':'dependency-'+str(i)+'.rpm'} for i in range(48)]
        stages=bootstrap.install_stages(Path('/fixed'),packages)
        self.assertEqual([row['package_count'] for row in stages],[1,48])
        self.assertIn('--nopost',stages[0]['argv']);self.assertEqual(stages[0]['argv'].count('--excludepath'),2)
        self.assertEqual(len(stages[1]['argv']),50)
        self.assertFalse(any(flag in row['argv'] for row in stages for flag in ('--noscripts','--notriggers','--nodeps')))
        self.assertNotIn('--nopost',stages[1]['argv'])
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.install_stages(Path('/fixed'),packages[:-1])

    def predecessor_fixture(self,change=None):
        before=[{'name':'baseline-'+str(i)} for i in range(921)]
        bundle={'sha256':'a'*64}
        common={'request':{'request_id':bootstrap.PREDECESSOR['request_id']},
          'execution':{'run_id':bootstrap.PREDECESSOR['run_id'],'workflow_commit':bootstrap.PREDECESSOR['workflow_commit']},
          'runtime_pin':bundle,'acquisition_sha256':bootstrap.PREDECESSOR['acquisition_sha256']}
        initial={**common,'status':'started'}
        prior={**common,'status':'failed','rpm_install_attempted':False,'rpm_install_completed':False,
          'error':{'type':'BootstrapError','message':'dependency would install unrelated privileged service or policy'},
          'before':{'preserved':True},'after_failure':{'preserved':True},
          'package_failure_observation':{'added':[],'removed':[],'partial_transaction_possible':False,'installed_packages':before}}
        if change: change(prior)
        intent=bootstrap.canonical(initial);result=bootstrap.canonical(prior)
        pins={**bootstrap.PREDECESSOR,'intent_sha256':bootstrap.digest(intent),'result_sha256':bootstrap.digest(result),
              'before_packages_sha256':bootstrap.digest(bootstrap.canonical(before))}
        return intent,result,{'before_packages':before},bundle,pins

    def test_predecessor_exact_receipts_are_required(self):
        intent,result,manifest,bundle,pins=self.predecessor_fixture()
        with mock.patch.object(bootstrap,'PREDECESSOR',pins):
            prior=bootstrap.predecessor_receipts(intent,result,manifest,bundle)
            self.assertEqual(prior['status'],'failed')
            with self.assertRaises(bootstrap.BootstrapError): bootstrap.predecessor_receipts(intent+b' ',result,manifest,bundle)
            with self.assertRaises(bootstrap.BootstrapError): bootstrap.predecessor_receipts(intent,result,manifest,{'sha256':'b'*64})

    def test_interrupted_or_mutated_predecessor_never_continues_implicitly(self):
        changes=(lambda x:x.update(rpm_install_attempted=True),
                 lambda x:x['package_failure_observation'].update(partial_transaction_possible=True),
                 lambda x:x['package_failure_observation'].update(added=[{'name':'new'}]),
                 lambda x:x.update(after_failure={'preserved':False}))
        for change in changes:
            intent,result,manifest,bundle,pins=self.predecessor_fixture(change)
            with mock.patch.object(bootstrap,'PREDECESSOR',pins),self.assertRaises(bootstrap.BootstrapError):
                bootstrap.predecessor_receipts(intent,result,manifest,bundle)

    def test_successor_guard_preserves_original_records_and_blocks_second_attempt(self):
        from types import SimpleNamespace
        intent,result,manifest,bundle,pins=self.predecessor_fixture()
        acquisition=bootstrap.canonical(manifest);pins={**pins,'acquisition_sha256':bootstrap.digest(acquisition)}
        # Rebind only this isolated receipt fixture; production constants stay
        # tied to the independently inspected native files.
        initial=bootstrap.decode(intent);initial['acquisition_sha256']=pins['acquisition_sha256']
        prior=bootstrap.decode(result);prior['acquisition_sha256']=pins['acquisition_sha256']
        intent=bootstrap.canonical(initial);result=bootstrap.canonical(prior)
        pins.update(intent_sha256=bootstrap.digest(intent),result_sha256=bootstrap.digest(result))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);stage=root/pins['request_id'];stage.mkdir()
            (root/'bootstrap-intent.json').write_bytes(intent);(root/'bootstrap-result.json').write_bytes(result)
            (stage/'operation-receipt.json').write_bytes(result);(stage/'acquisition.json').write_bytes(acquisition)
            def fixture_lstat(path):
                value=os.lstat(path)
                return SimpleNamespace(st_mode=value.st_mode,st_uid=0)
            with mock.patch.object(bootstrap,'PREDECESSOR',pins),mock.patch.object(bootstrap,'BOOTSTRAP_STATE',root),\
                 mock.patch.object(bootstrap,'PREFIX',root/'prefix'),mock.patch.object(bootstrap,'CONFIG',root/'config'),\
                 mock.patch.object(bootstrap,'rooted',side_effect=lambda path,mode:Path(path)),\
                 mock.patch.object(Path,'lstat',new=fixture_lstat):
                request={'request_id':'72efac38-891b-449e-b538-fd09dd2319c6'}
                _,old_intent,old_result,marker=bootstrap.prepare_successor(manifest,bundle,request)
                self.assertEqual(old_intent,intent);self.assertEqual(old_result,result)
                marker.write_text('retained successor intent')
                with self.assertRaisesRegex(bootstrap.BootstrapError,'existing or partial successor'):
                    bootstrap.prepare_successor(manifest,bundle,request)
            self.assertEqual((root/'bootstrap-intent.json').read_bytes(),intent)
            self.assertEqual((root/'bootstrap-result.json').read_bytes(),result)

    def test_exclusion_state_is_required_after_package_install(self):
        unit=b'MainPID=0\nLoadState=not-found\nActiveState=inactive\nSubState=dead\nFragmentPath=\n'
        states=(''.join(path+'\t2\n' for path in bootstrap.ZVBI['excluded_paths'])).encode()
        with mock.patch.object(Path,'exists',return_value=False),mock.patch.object(Path,'is_symlink',return_value=False):
            with mock.patch.object(bootstrap,'command',side_effect=[unit,states]):
                result=bootstrap.daemon_absence(Path('/logs'),'test',True)
                self.assertEqual(set(result['excluded_file_states'].values()),{'2'})
            with mock.patch.object(bootstrap,'command',side_effect=[unit,states.replace(b'\t2',b'\t0')]):
                with self.assertRaises(bootstrap.BootstrapError): bootstrap.daemon_absence(Path('/logs'),'test',True)

    def test_output_ancestry_symlink_is_rejected_before_privileged_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);real=root/'real';real.mkdir();(root/'linked').symlink_to(real,target_is_directory=True)
            with self.assertRaises(OSError): bootstrap.operation_directory(root/'linked')

    def test_root_evidence_leaf_stays_private_during_nested_write_and_ordinary_failure(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outside=root/'outside';outside.mkdir()
            real_fstat=os.fstat
            def root_info(fd):
                value=real_fstat(fd);return SimpleNamespace(st_uid=0,st_mode=value.st_mode)
            def operation(*args):
                fd=args[-1];held=Path('/proc/self/fd')/str(fd)
                self.assertEqual(os.stat(held).st_mode&0o777,0o700);ownership.assert_not_called()
                (root/'root-evidence').rename(root/'retained-leaf')
                (root/'root-evidence').symlink_to(outside,target_is_directory=True)
                (held/'evidence.txt').write_bytes(b'fixed raw evidence')
                self.assertEqual(list(outside.iterdir()),[])
                raise bootstrap.BootstrapError('controlled failure')
            old_umask=os.umask(0o022)
            try:
                with mock.patch.object(bootstrap.os,'geteuid',return_value=0),\
                     mock.patch.object(bootstrap.platform,'machine',return_value='aarch64'),\
                     mock.patch.object(bootstrap.sys,'version_info',(3,9)),mock.patch.object(bootstrap,'validate_request'),\
                     mock.patch.object(bootstrap,'operation_directory',side_effect=lambda path:os.open(path,os.O_RDONLY|os.O_DIRECTORY)),\
                     mock.patch.object(bootstrap.os,'fstat',side_effect=root_info),\
                     mock.patch.object(bootstrap.os,'fchown') as ownership,\
                     mock.patch.object(bootstrap,'install_owned',side_effect=operation):
                    with self.assertRaisesRegex(bootstrap.BootstrapError,'controlled failure'):
                        bootstrap.install(None,None,None,None,None,None,root)
                    self.assertEqual(ownership.call_count,1);self.assertEqual(ownership.call_args.args[1:],(1000,1000))
                self.assertEqual((root/'retained-leaf/evidence.txt').read_bytes(),b'fixed raw evidence')
            finally: os.umask(old_umask)

    def test_rejected_replaced_leaf_is_never_given_to_runner(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old_umask=os.umask(0o022)
            try:
                with mock.patch.object(bootstrap.os,'geteuid',return_value=0),\
                     mock.patch.object(bootstrap.platform,'machine',return_value='aarch64'),\
                     mock.patch.object(bootstrap.sys,'version_info',(3,9)),mock.patch.object(bootstrap,'validate_request'),\
                     mock.patch.object(bootstrap,'operation_directory',side_effect=lambda path:os.open(path,os.O_RDONLY|os.O_DIRECTORY)),\
                     mock.patch.object(bootstrap.os,'fstat',return_value=SimpleNamespace(st_uid=999,st_mode=0o40700)),\
                     mock.patch.object(bootstrap.os,'fchown') as ownership,mock.patch.object(bootstrap,'install_owned') as operation:
                    with self.assertRaisesRegex(bootstrap.BootstrapError,'root-owned evidence leaf'):
                        bootstrap.install(None,None,None,None,None,None,root)
                    ownership.assert_not_called();operation.assert_not_called()
            finally: os.umask(old_umask)

    def test_artifact_redirects_fail_closed(self):
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.FixedRedirect().redirect_request(None,None,302,'',{},'https://example.net/redirect')


if __name__=='__main__': unittest.main(verbosity=2)
