"""Validate a finished browser episode, then publish exact canonical evidence.

Run outside the untrusted renderer after it stops. This writer is deliberately
separate from the existing private read service. No URL is rewritten to satisfy
the context bridge: query-bearing and HTTP sources remain canonical observations
with an explicit ineligible context-intake status.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

from dot_ai_os.bridge import DotContextBridge
from .browser_egress import canonical, unique_json
from .browser_policy import BrowserLimits, BrowserPolicyError, public_ip, public_url
from .project_registry import MerlinRegistry


def digest(raw): return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition: raise BrowserPolicyError(message)


def timestamp(value):
    require(isinstance(value,str) and len(value)<=80,'invalid capture time')
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(parsed.tzinfo is not None,'capture time requires timezone')
    return parsed


def validate_episode(directory):
    """Verify bytes, protocol lineage and source binding, not website truth."""
    root=Path(directory)
    require(root.is_dir() and not root.is_symlink(),'episode directory required')
    manifest_path=root/'episode.json'
    require(manifest_path.is_file() and not manifest_path.is_symlink() and manifest_path.stat().st_size<=131072,
            'bounded final manifest required')
    raw=manifest_path.read_bytes();manifest=unique_json(raw)
    require(isinstance(manifest,dict) and canonical(manifest)==raw,'canonical manifest required')
    fields={'schema','episode_id','started_at','completed_at','status','engine','isolation','limits',
            'observations','actions','files','events','event_chain_head','counts','model_calls',
            'external_model_cost_usd','qualification','promotion_authority','policy','error_type'}
    require(set(manifest)==fields and manifest['schema']=='merlin-public-browser-episode/1','invalid episode schema')
    require(isinstance(manifest['episode_id'],str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',manifest['episode_id']),
            'invalid episode identity')
    limits=BrowserLimits(**manifest['limits'])
    require(manifest['status'] in ('completed','completed_with_failures','failed'),'invalid episode status')
    require(timestamp(manifest['completed_at'])>=timestamp(manifest['started_at']),'episode chronology differs')
    require(type(manifest['model_calls']) is int and manifest['model_calls']==0
            and type(manifest['external_model_cost_usd']) is int and manifest['external_model_cost_usd']==0
            and manifest['qualification'] is False and manifest['promotion_authority'] is False,
            'browser episode cannot confer authority or model budget')
    require(isinstance(manifest['files'],list) and len(manifest['files'])<=320,'bounded artifact inventory required')
    files={};refs={};total=0
    for ref in manifest['files']:
        require(isinstance(ref,dict) and set(ref)=={'path','sha256','bytes','media_type'},'invalid artifact reference')
        name=ref['path']
        require(isinstance(name,str) and len(name)<=200 and re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+',name)
                and '..' not in Path(name).parts and name not in refs and name!='episode.json','invalid artifact path')
        require(type(ref['bytes']) is int and 0<=ref['bytes']<=limits.max_evidence_bytes
                and isinstance(ref['sha256'],str) and re.fullmatch('[0-9a-f]{64}',ref['sha256'])
                and isinstance(ref['media_type'],str) and 1<=len(ref['media_type'])<=100,'invalid artifact identity')
        path=root/name
        require(all(not (root/part).is_symlink() for part in [str(p) for p in Path(name).parents if str(p)!='.']),
                'symlink artifact parent denied')
        info=path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size==ref['bytes'],'artifact file differs')
        total+=info.st_size
        require(total+len(raw)<=limits.max_evidence_bytes,'evidence byte budget exceeded')
        content=path.read_bytes()
        require(digest(content)==ref['sha256'],'artifact digest differs')
        refs[name]=ref;files[name]=content
    actual=set()
    for ordinal,path in enumerate(root.rglob('*'),1):
        require(ordinal<=512,'bounded evidence filesystem required')
        require(not path.is_symlink(),'unexpected symlink in evidence')
        if not path.is_dir():
            require(path.is_file(),'unexpected nonregular evidence file')
            actual.add(str(path.relative_to(root)))
    require(actual==set(files)|{'episode.json'},'unlisted or missing episode evidence')
    counts=manifest['counts']
    require(isinstance(counts,dict) and set(counts)=={'actions','requests','response_body_bytes','artifact_bytes'},'invalid counts')
    require(all(type(value) is int and value>=0 for value in counts.values()),'integer counts required')
    require(counts['artifact_bytes']==total and counts['requests']<=limits.max_requests+1
            and counts['response_body_bytes']<=limits.max_network_bytes+1,'episode counts exceed bounds')

    def referenced(ref):
        require(isinstance(ref,dict) and refs.get(ref.get('path'))==ref,'reference is not an exact inventoried artifact')
        return files[ref['path']]

    require(isinstance(manifest['events'],list) and 1<=len(manifest['events'])<=200,'bounded event sequence required')
    chain='0'*64;events=[];event_by_path={};resources={};observed_actions={};started_actions={}
    trace_spent=0;trace_gaps=False
    for number,ref in enumerate(manifest['events'],1):
        event_raw=referenced(ref);value=unique_json(event_raw)
        require(canonical(value)==event_raw and set(value)=={'sequence','previous_sha256','recorded_at','event','event_sha256'},
                'invalid event envelope')
        require(ref['path']=='events/%04d.json'%number and value['sequence']==number
                and value['previous_sha256']==chain,'event sequence or chain differs')
        claimed=value['event_sha256'];body={key:item for key,item in value.items() if key!='event_sha256'}
        require(claimed==digest(canonical(body)),'event digest differs');chain=claimed
        timestamp(value['recorded_at']);event=value['event'];require(isinstance(event,dict),'invalid event payload')
        kind=event.get('kind')
        require(kind in {'resource','resource_trace_budget_exhausted','observation','action_started','action_finished',
                         'browser_started','episode_error','episode_finished'},'unknown event kind')
        if kind=='resource':
            require(event['resource_id']=='r%04d'%(len(resources)+1),'resource sequence differs')
            require(event['outcome'] in ('fulfilled','denied'),'invalid resource outcome')
            require(type(event['consumed_body_bytes']) is int and event['consumed_body_bytes']>=0
                    and event['episode_response_body_bytes']==trace_spent+event['consumed_body_bytes'],
                    'resource byte ledger differs')
            trace_spent=event['episode_response_body_bytes']
            if event['outcome']=='fulfilled':
                require(public_url(event['url'])==event['url'] and event['method'] in ('GET','HEAD')
                        and type(event['status']) is int and 100<=event['status']<=599
                        and event['tls_verified'] is (urlsplit(event['url']).scheme=='https')
                        and isinstance(event['body_sha256'],str) and re.fullmatch('[0-9a-f]{64}',event['body_sha256'])
                        and type(event['body_bytes']) is int and 0<=event['body_bytes']<=limits.max_resource_bytes,
                        'invalid fulfilled resource')
                public_ip(event['peer_ip'])
                if event['main_document']:
                    response=referenced(event['body_ref'])
                    require(digest(response)==event['body_sha256'] and len(response)==event['body_bytes'],
                            'main document response bytes differ')
            resources[event['resource_id']]=event
        elif kind=='resource_trace_budget_exhausted':
            trace_gaps=True
            require(type(event['episode_response_body_bytes']) is int and event['episode_response_body_bytes']>=trace_spent,
                    'failure resource ledger regressed')
            trace_spent=event['episode_response_body_bytes']
        elif kind=='action_started':
            require(event['action_id'] not in started_actions,'duplicate action start')
            started_actions[event['action_id']]=event
        elif kind=='action_finished':
            require(event['id'] not in observed_actions,'duplicate action finish')
            observed_actions[event['id']]={key:item for key,item in event.items() if key!='kind'}
        events.append(event);event_by_path[ref['path']]=event
    require(chain==manifest['event_chain_head'] and events[-1]['kind']=='episode_finished'
            and events[-1]['status']==manifest['status'],'episode ending differs')
    require(counts['requests']==len(resources)+(1 if trace_gaps else 0)
            and counts['response_body_bytes']==trace_spent,'final resource counts differ')
    require(isinstance(manifest['actions'],list) and len(manifest['actions'])<=limits.max_actions
            and counts['actions']==len(manifest['actions']),'action count differs')
    action_map={}
    for number,action in enumerate(manifest['actions'],1):
        require(action['id']=='a%04d'%number and observed_actions.get(action['id'])==action,'action lineage differs')
        require(action['status'] in ('succeeded','failed'),'invalid action outcome')
        request=referenced(action['request_ref']);require(canonical(unique_json(request))==request,'action bytes are not canonical')
        if action['id'] in started_actions:
            require(started_actions[action['id']]['request_ref']==action['request_ref'],'action request binding differs')
        else: require(action['status']=='failed','successful action has no start')
        action_map[action['id']]=action
    require(set(observed_actions)==set(action_map) and set(started_actions)<=set(action_map),'unindexed action event')
    require(isinstance(manifest['observations'],list) and len(manifest['observations'])<=len(action_map),'observation count differs')
    observations=[];seen={};observation_actions=set();observation_paths=set()
    for number,index in enumerate(manifest['observations'],1):
        require(set(index)=={'id','action_id','event_ref'} and index['id']=='o%04d'%number,'invalid observation index')
        referenced(index['event_ref']);event=event_by_path.get(index['event_ref']['path'])
        require(event and event['kind']=='observation','observation event missing')
        item=event['observation']
        require(item['id']==index['id'] and item['action_id']==index['action_id'] and item['action_id'] in action_map,
                'observation action binding differs')
        require(item['action_id'] not in observation_actions,'multiple captures reassigned to one action')
        observation_actions.add(item['action_id']);observation_paths.add(index['event_ref']['path'])
        require(public_url(item['url'])==item['url']==item['document_url'],'rendered source URL differs')
        resource=resources.get(item['document_resource_id'])
        require(resource and resource['outcome']=='fulfilled' and resource['main_document']
                and resource['url']==item['document_url'] and resource['status']==item['document_status']
                and resource['tls_verified'] is item['document_tls_verified'],'document source binding differs')
        require(item['qualification'] is False and item['epistemic']=='source_snapshot','observation cannot self-qualify')
        timestamp(item['captured_at'])
        require(isinstance(item['title'],str) and len(item['title'])<=500,'invalid document title')
        require(set(item['artifacts'])=={'text','dom','screenshot','response_body'},'invalid capture artifact set')
        for kind,bound in (('text',limits.max_text_bytes),('dom',limits.max_dom_bytes),
                           ('screenshot',limits.max_screenshot_bytes),('response_body',limits.max_resource_bytes)):
            content=referenced(item['artifacts'][kind]);require(len(content)<=bound,'capture artifact byte budget exceeded')
            if kind in ('text','dom'): content.decode('utf-8')
            if kind=='screenshot': require(content.startswith(b'\x89PNG\r\n\x1a\n'),'viewport is not a PNG')
        require(item['artifacts']['response_body']==resource['body_ref'],'observation response reference differs')
        require(isinstance(item['links'],list) and len(item['links'])<=limits.max_links,'link count exceeds budget')
        for ordinal,link in enumerate(item['links'],1):
            require(set(link)=={'id','url','text'} and link['id']==item['id']+':l%03d'%ordinal
                    and public_url(link['url'])==link['url'] and isinstance(link['text'],str) and len(link['text'])<=500,
                    'invalid observed link')
        seen[item['id']]=item;observations.append(item)
    require(observation_paths=={path for path,event in event_by_path.items() if event['kind']=='observation'},
            'unindexed observation event')
    for action in action_map.values():
        if action['status']=='succeeded':
            require(action['observation_id'] in seen and seen[action['observation_id']]['action_id']==action['id'],
                    'successful action lacks its own observation')
    if manifest['status']=='completed':
        require(action_map and all(item['status']=='succeeded' for item in action_map.values()) and not trace_gaps,
                'completed status contradicts failures')
    if observations:
        engine=manifest['engine'];isolation=manifest['isolation']
        require(engine.get('name')=='chromium' and engine.get('chromium_sandbox') is True
                and isinstance(engine.get('browser_version'),str) and engine['browser_version'],
                'rendered capture engine metadata required')
        require(type(isolation.get('uid')) is int and isolation['uid']>0 and isolation.get('euid')==isolation['uid']
                and isolation.get('interfaces')==['lo'] and isolation.get('effective_capabilities')==0
                and isolation.get('no_new_privileges') is True and isolation.get('direct_external_network') is False,
                'observed renderer isolation metadata required')
        # This is metadata consistency, not independent kernel/runtime attestation.
        # The operator's pinned launcher receipt supplies that external evidence.
    return {'manifest':manifest,'manifest_bytes':raw,'manifest_sha256':digest(raw),
            'files':files,'file_refs':refs,'observations':observations,'events':events}


def publish_episode(directory, registry, *, project_id='merlin-browser-research'):
    checked=validate_episode(directory);manifest=checked['manifest'];episode=manifest['episode_id']
    base='browser/episodes/'+episode
    try:
        prior=registry.artifact_ref(project_id,base+'/publication.json')
    except (KeyError,FileNotFoundError): prior=None
    if prior is not None:
        previous=unique_json(registry.read_artifact_ref(prior,max_bytes=262144)['content'])
        require(previous['manifest_sha256']==checked['manifest_sha256'],'episode identity is already used')
        return previous
    bridge=DotContextBridge(registry,project_id=project_id,namespaces=('rsi',))
    bridge.initialize()
    artifacts={}
    for path,raw in checked['files'].items():
        logical=base+'/'+path
        registry.put_artifact(project_id,logical,raw,checked['file_refs'][path]['media_type'])
        artifacts[path]=registry.artifact_ref(project_id,logical)
    registry.put_artifact(project_id,base+'/episode.json',checked['manifest_bytes'],'application/json')
    manifest_ref=registry.artifact_ref(project_id,base+'/episode.json')
    sources=[];source_refs=[]
    for observation in checked['observations']:
        url=observation['document_url'];parsed=urlsplit(url)
        text=checked['files'][observation['artifacts']['text']['path']]
        item={'observation_id':observation['id'],'acquisition_url':url,
              'capture_event_ref':artifacts[next(index['event_ref']['path'] for index in manifest['observations'] if index['id']==observation['id'])],
              'artifacts':{name:artifacts[ref['path']] for name,ref in observation['artifacts'].items()},
              'context_intake':'ineligible_url_contract','source_ref':None,'qualification':False}
        if parsed.scheme=='https' and not parsed.query and not parsed.fragment and len(url)<=2000:
            action=next(item for item in manifest['actions'] if item['id']==observation['action_id'])
            if action['status']!='succeeded': item['context_intake']='action_not_completed'
            elif not (200<=observation['document_status']<300): item['context_intake']='http_status_not_success'
            elif not text or not text.decode().strip(): item['context_intake']='empty_rendered_text'
            else:
                try:
                    ingested=bridge.ingest(namespace='rsi',source_id='public-browser:'+episode+':'+observation['id'],
                        title=observation['title'].strip() or ('Public source '+parsed.hostname)[:500],content=text,
                        source_url=url,source_version='browser-capture-sha256:'+observation['artifacts']['text']['sha256'],
                        epistemic='source_snapshot',captured_at=observation['captured_at'])
                except ValueError as error:
                    if str(error)!='context record ceiling reached; shard the source set': raise
                    item['context_intake']='context_capacity_exhausted'
                else:
                    item.update(context_intake='source_snapshot',source_ref=ingested['source_ref'],record_ref=ingested['record_ref'])
                    source_refs.append(ingested['source_ref'])
        sources.append(item)
    handoff={'schema':'merlin-browser-handoff/1','episode_id':episode,'manifest_ref':manifest_ref,
             'manifest_sha256':checked['manifest_sha256'],'sources':sources,
             'source_refs':source_refs,'status':manifest['status'],
             'next_action':'Review untrusted captured evidence and navigation outcomes before proposing a measured research change.',
             'authority':'context_only','qualification':False,'promotion_authority':False,'model_calls':0}
    registry.put_artifact(project_id,base+'/handoff.json',canonical(handoff),'application/json')
    handoff_ref=registry.artifact_ref(project_id,base+'/handoff.json')
    context_handoff_ref=None
    if source_refs:
        context_handoff_ref=bridge.save_handoff('browser-'+episode,
            summary='Rendered public web captures; source integrity only. Full acquisition/action evidence: '+base+'/handoff.json',
            next_action=handoff['next_action'],source_refs=source_refs)['handoff_ref']
    result={'schema':'merlin-browser-publication/1','episode_id':episode,'manifest_sha256':checked['manifest_sha256'],
            'manifest_ref':manifest_ref,'handoff_ref':handoff_ref,'context_handoff_ref':context_handoff_ref,
            'artifacts':artifacts,'sources':sources,'status':manifest['status'],
            'qualification':False,'promotion_authority':False,'model_calls':0}
    registry.put_artifact(project_id,base+'/publication.json',canonical(result),'application/json')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode-directory',required=True,type=Path)
    parser.add_argument('--registry-root',required=True,type=Path)
    parser.add_argument('--project-id',default='merlin-browser-research')
    args=parser.parse_args()
    print(canonical(publish_episode(args.episode_directory,MerlinRegistry(args.registry_root),project_id=args.project_id)).decode())


if __name__=='__main__': main()
