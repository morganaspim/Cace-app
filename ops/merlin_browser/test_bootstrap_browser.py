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
                 'operation':'bootstrap','created_at':'2026-11-21T00:00:00Z'}
        execution={'runner':'cace-oci-a1','run_id':1,'run_attempt':1,'workflow_commit':'a'*40}
        bootstrap.validate_request(request,execution)
        for extra in ('command','url','packages','budget'):
            with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_request({**request,extra:'value'},execution)
        with self.assertRaises(bootstrap.BootstrapError): bootstrap.validate_request(request,{**execution,'run_attempt':2})

    def test_artifact_redirects_fail_closed(self):
        with self.assertRaises(bootstrap.BootstrapError):
            bootstrap.FixedRedirect().redirect_request(None,None,302,'',{},'https://example.net/redirect')


if __name__=='__main__': unittest.main(verbosity=2)
