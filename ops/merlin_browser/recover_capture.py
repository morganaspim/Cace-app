"""Derive one explicitly pinned saved-capture ledger; never reacquire or edit raw.

Only the proved run44946846703 arXiv trace is admitted. The strict browser
importer remains unchanged. Original observations and source bytes remain raw;
a separate derivative chain carries an explicit operator provenance artifact.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SOURCE_EPISODE='database-arxiv-18106dfc-0a56-4b68-9d30-5d334d7d6a69'
DERIVED_EPISODE='recovered-arxiv-18106dfc-0a56-4b68-9d30-5d334d7d6a69'
SOURCE_MANIFEST='91d4756d9799cd633e78164cde97ed6be11381550171250d4109f156121f5541'
SOURCE_CHAIN='3ec9c1f810897fda7abd222103b7f9bd675bffbd1867fcc1800fbb8c19addbe2'
SOURCE_LAUNCH='6a34e725a31daebbbaf6a51e358101cb01d2e075118b501f6f19a3c4887236c0'
SOURCE_ARTIFACT='854938680e410a54ce05907cc7f84c2b98a526b25aedfe2a0e0331142994b20a'
SOURCE_COMMIT='c8b61b30dfff6c1e3c7889595276d27adca7b5be'
SOURCE_RUN=44946846703
PROVENANCE_PATH='recovery/derivation.json'


class RecoveryError(RuntimeError): pass


def require(value,message):
    if not value: raise RecoveryError(message)


def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def digest(raw): return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result={}
    for key,value in pairs:
        require(key not in result,'duplicate JSON key');result[key]=value
    return result


def decode(raw): return json.loads(raw,object_pairs_hook=unique,
    parse_constant=lambda _:(_ for _ in ()).throw(RecoveryError('nonfinite JSON')))


def read_regular(path,maximum=2*1024*1024):
    path=Path(path);require(path.is_absolute() and '..' not in path.parts,'absolute evidence path required')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
        leaf=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    finally: os.close(fd)
    try:
        before=os.fstat(leaf)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=maximum,'bounded regular original required')
        raw=bytearray()
        while True:
            part=os.read(leaf,min(65536,maximum+1-len(raw)))
            if not part: break
            raw.extend(part);require(len(raw)<=maximum,'original evidence ceiling')
        after=os.fstat(leaf)
        require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
                (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'original changed while read')
        return bytes(raw)
    finally: os.close(leaf)


def safe_name(name):
    require(isinstance(name,str) and len(name)<=200 and
        re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+',name) and '..' not in Path(name).parts,
        'bounded original member name required')
    return name


def ledger_proof(resources,expected_requests=31,expected_total=738314):
    require(len(resources)==expected_requests,'exact complete resource count required')
    prefixes=[0]
    for index,event in enumerate(resources,1):
        require(event.get('resource_id')=='r%04d'%index and event.get('outcome')=='fulfilled'
            and event.get('method')=='GET' and type(event.get('body_bytes')) is int
            and 0<=event['body_bytes']<=1048576,'only complete fulfilled GET body records admitted')
        prefixes.append(prefixes[-1]+event['body_bytes'])
    require(prefixes[-1]==expected_total,'exact final body-byte conservation required')
    previous_end=0;mapping=[]
    for index,event in enumerate(resources):
        consumed=event.get('consumed_body_bytes');end=event.get('episode_response_body_bytes')
        require(type(consumed) is int and type(end) is int and consumed>=0
            and end-consumed==prefixes[index],'overlap start must equal the exact preceding body prefix')
        require(end in prefixes[index+1:] and end>=previous_end,
            'each completion watermark must be a monotonic later complete prefix')
        mapping.append({'resource_id':event['resource_id'],'body_bytes':event['body_bytes'],
            'original_consumed_body_bytes':consumed,'original_episode_response_body_bytes':end,
            'derived_consumed_body_bytes':event['body_bytes'],'derived_episode_response_body_bytes':prefixes[index+1]})
        previous_end=end
    require(previous_end==expected_total,'exact terminal broker counter required')
    return mapping


def inspect_original(directory):
    root=Path(directory).absolute();raw=read_regular(root/'episode.json',131072)
    require(len(raw)==13740 and digest(raw)==SOURCE_MANIFEST,'only the exact retained arXiv manifest is admitted')
    manifest=decode(raw);require(canonical(manifest)==raw,'canonical original manifest required')
    require(manifest.get('schema')=='merlin-public-browser-episode/1' and manifest.get('episode_id')==SOURCE_EPISODE
        and manifest.get('status')=='completed' and manifest.get('event_chain_head')==SOURCE_CHAIN
        and manifest.get('counts',{}).get('requests')==31 and manifest['counts']['response_body_bytes']==738314,
        'exact retained completed acquisition required')
    rows=manifest.get('files');require(isinstance(rows,list) and len(rows)==41,'exact original inventory required')
    files={};total=0
    for row in rows:
        name=safe_name(row['path']);require(name not in files and name!='episode.json','unique original members required')
        body=read_regular(root/name)
        require(len(body)==row['bytes'] and digest(body)==row['sha256'],'original inventoried identity differs')
        files[name]=body;total+=len(body);require(total<=1048576,'fixed original evidence total ceiling')
    actual=set()
    for ordinal,path in enumerate(root.rglob('*'),1):
        require(ordinal<=128 and not path.is_symlink(),'bounded link-free original tree required')
        if not path.is_dir(): actual.add(str(path.relative_to(root)))
    require(actual==set(files)|{'episode.json'} and total==manifest['counts']['artifact_bytes'],
        'exact raw original filesystem and byte count required')
    chain='0'*64;events=[];resources=[]
    require(len(manifest['events'])==36,'exact original event count required')
    for number,ref in enumerate(manifest['events'],1):
        require(ref['path']=='events/%04d.json'%number,'original event path sequence differs')
        body=files[ref['path']];require(len(body)==ref['bytes'] and digest(body)==ref['sha256'],'original event ref differs')
        event=decode(body)
        require(canonical(event)==body and set(event)=={'sequence','previous_sha256','recorded_at','event','event_sha256'}
            and event['sequence']==number and event['previous_sha256']==chain,'original canonical event chain differs')
        content={key:value for key,value in event.items() if key!='event_sha256'}
        require(digest(canonical(content))==event['event_sha256'],'original event envelope hash differs')
        chain=event['event_sha256'];events.append(event)
        if event['event'].get('kind')=='resource': resources.append(event['event'])
        require(event['event'].get('kind') not in ('resource_trace_budget_exhausted','episode_error'),
            'failed or incomplete original trace cannot be repaired by this operation')
    require(chain==SOURCE_CHAIN and resources[-1]['episode_response_body_bytes']==738314,'original terminal counter differs')
    mapping=ledger_proof(resources)
    require(all(event['event'].get('kind')!='action_finished' or event['event'].get('status')=='succeeded' for event in events),
        'failed actions are outside this exact recovery')
    return {'manifest':manifest,'manifest_bytes':raw,'files':files,'events':events,'mapping':mapping}


def derive_bytes(checked):
    manifest=copy.deepcopy(checked['manifest']);files=dict(checked['files']);mapping=checked['mapping']
    corrected={row['resource_id']:row for row in mapping};chain='0'*64;event_mapping=[]
    for original in checked['events']:
        event=copy.deepcopy(original);body=event['event'];path='events/%04d.json'%event['sequence']
        if body.get('kind')=='resource':
            row=corrected[body['resource_id']]
            body['consumed_body_bytes']=row['derived_consumed_body_bytes']
            body['episode_response_body_bytes']=row['derived_episode_response_body_bytes']
        event['previous_sha256']=chain;event.pop('event_sha256')
        event['event_sha256']=digest(canonical(event));chain=event['event_sha256']
        files[path]=canonical(event)
        event_mapping.append({'path':path,'original_sha256':digest(checked['files'][path]),
            'derived_sha256':digest(files[path]),'original_event_sha256':original['event_sha256'],
            'derived_event_sha256':chain})
    provenance={'schema':'merlin-browser-ledger-recovery/1','derivation_kind':'operator_reconstructed_resource_accounting',
        'source_episode_id':SOURCE_EPISODE,'derived_episode_id':DERIVED_EPISODE,'source_run_id':SOURCE_RUN,
        'source_workflow_commit':SOURCE_COMMIT,'source_artifact_sha256':SOURCE_ARTIFACT,
        'source_manifest_sha256':SOURCE_MANIFEST,'source_event_chain_head':SOURCE_CHAIN,'source_launch_receipt_sha256':SOURCE_LAUNCH,
        'derived_event_chain_head':chain,'original_files':checked['manifest']['files'],'resource_mapping':mapping,
        'event_mapping':event_mapping,'original_capture_started_at':manifest['started_at'],
        'original_capture_completed_at':manifest['completed_at'],'network_reacquired':False,'model_calls':0,
        'original_bytes_modified':False,'new_browser_execution':False,'qualification':False,'promotion_authority':False,
        'observed_proof':{'resources':31,'all_fulfilled_get':True,'sum_body_bytes':738314,'final_broker_counter':738314,
            'every_overlap_start_is_prior_body_prefix':True,'every_completion_is_monotonic_later_prefix':True},
        'mechanism_inference':'Playwright route fulfillment yielded to further callbacks before the old mutable counter was recorded.',
        'changed_fields':['resource consumed_body_bytes','resource episode_response_body_bytes','event hash chain',
            'event artifact references','derivative episode_id','artifact inventory and byte count','policy provenance note'],
        'limitations':['The derivative is operator evidence, not a new native acquisition or original renderer hash chain.',
            'Original source bytes, URLs, capture times, statuses, engine/isolation records and resource metadata remain retained.',
            'This proof admits only the pinned complete arXiv trace and does not relax the strict episode importer.']}
    files[PROVENANCE_PATH]=canonical(provenance)
    refs={row['path']:{**row,'bytes':len(files[row['path']]),'sha256':digest(files[row['path']])} for row in manifest['files']}
    refs[PROVENANCE_PATH]={'path':PROVENANCE_PATH,'bytes':len(files[PROVENANCE_PATH]),'sha256':digest(files[PROVENANCE_PATH]),
        'media_type':'application/json'}
    manifest['episode_id']=DERIVED_EPISODE;manifest['event_chain_head']=chain
    manifest['files']=[refs[row['path']] for row in manifest['files']]+[refs[PROVENANCE_PATH]]
    manifest['events']=[refs[row['path']] for row in manifest['events']]
    for row in manifest['observations']: row['event_ref']=refs[row['event_ref']['path']]
    manifest['counts']['artifact_bytes']=sum(len(body) for body in files.values())
    manifest['policy']+=' Operator-derived accounting recovery: see recovery/derivation.json; no new acquisition or original-trace relabeling.'
    manifest_raw=canonical(manifest)
    require(len(manifest_raw)<=131072 and len(files)==42,'bounded derivative manifest required')
    return {'manifest':manifest,'manifest_bytes':manifest_raw,'files':files,'provenance':provenance,
        'provenance_sha256':digest(files[PROVENANCE_PATH]),'manifest_sha256':digest(manifest_raw)}


def write_derived(checked,destination):
    destination=Path(destination);require(destination.is_absolute() and not destination.exists()
        and not destination.is_symlink(),'new absolute derivative directory required')
    derived=derive_bytes(checked);destination.mkdir(mode=0o700)
    for name,raw in list(derived['files'].items())+[('episode.json',derived['manifest_bytes'])]:
        target=destination/safe_name(name);target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        descriptor=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(descriptor,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return derived
