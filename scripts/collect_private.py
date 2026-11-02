"""Merge account-owned private metadata only. Never print API bodies or errors."""
import json
import os
import pathlib
import sys
import urllib.request
import urllib.error

OWNER = "azdeenzack"
QUERY = '''query($cursor:String) { viewer { login repositories(first:100,after:$cursor,ownerAffiliations:[OWNER],privacy:PRIVATE) { nodes { databaseId visibility isFork primaryLanguage { name color } } pageInfo { hasNextPage endCursor } } } }'''

class CollectionFailure(Exception):
    def __init__(self, code=1):
        self.code=code

class ApiRejected(CollectionFailure):
    pass

def merge(snapshot, fetch):
    result = json.loads(json.dumps(snapshot))
    seen = {r['repository_id'] for r in result['repositories']}
    cursor = None
    cursors = set()
    while True:
        response = fetch(cursor)
        if not isinstance(response, dict):
            raise CollectionFailure(31)
        if response.get('errors'):
            raise ApiRejected()
        viewer = response['data']['viewer']
        if viewer['login'].lower() != OWNER:
            raise CollectionFailure(32)
        connection = viewer['repositories']
        nodes = connection['nodes']
        if not isinstance(nodes, list) or len(nodes) > 100:
            raise CollectionFailure(33)
        for node in nodes:
            if node['visibility'] != 'PRIVATE' or type(node['databaseId']) is not int or type(node['isFork']) is not bool:
                raise CollectionFailure(34)
            rid = node['databaseId']
            if rid in seen:
                raise CollectionFailure(35)
            seen.add(rid)
            language = node['primaryLanguage']
            name = None
            if language is not None:
                name, color = language['name'], language['color']
                if not isinstance(name,str) or len(name)>100 or (color is not None and (not isinstance(color,str) or len(color)!=7 or color[0]!='#' or any(c not in '0123456789abcdefABCDEF' for c in color[1:]))):
                    raise CollectionFailure(36)
                color = color.lower() if color is not None else None
                existing = result['language_colors'].get(name, color)
                existing = existing.lower() if isinstance(existing, str) else existing
                if existing != color:
                    raise CollectionFailure(37)
                result['language_colors'][name] = color
            result['repositories'].append({'repository_id':rid,'visibility':'private','is_fork':node['isFork'],'primary_language':name})
        page = connection['pageInfo']
        if type(page['hasNextPage']) is not bool:
            raise CollectionFailure(38)
        if not page['hasNextPage']:
            break
        cursor = page['endCursor']
        if not isinstance(cursor,str) or not cursor or cursor in cursors:
            raise CollectionFailure(39)
        cursors.add(cursor)
    return result

def main():
    # Input/output paths fixed by trusted workflow. No command-line secret.
    token = os.environ.pop('KOI_PRIVATE_METADATA_TOKEN', '')
    if not token or len(sys.argv) != 3:
        raise CollectionFailure(40)
    def fetch(cursor):
        request = urllib.request.Request('https://api.github.com/graphql',
            data=json.dumps({'query':QUERY,'variables':{'cursor':cursor}}).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'self-owned-koi'},method='POST')
        # Explicitly forbid redirects to avoid forwarding Authorization.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):
                raise CollectionFailure(41)
        with urllib.request.build_opener(NoRedirect).open(request,timeout=30) as response:
            data=response.read(2_000_001)
            if len(data)>2_000_000:
                raise CollectionFailure(42)
            return json.loads(data)
    snapshot=json.loads(pathlib.Path(sys.argv[1]).read_text())
    result=merge(snapshot,fetch)
    path=pathlib.Path(sys.argv[2])
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:
        json.dump(result,f)
    return 0

if __name__=='__main__':
    try:
        sys.exit(main())
    except urllib.error.HTTPError as error:
        # Fixed numeric classifications only. Never disclose payload, URL or exception.
        sys.exit({401:11,403:12,429:13}.get(error.code,14))
    except ApiRejected:
        sys.exit(20)
    except CollectionFailure as error:
        sys.stderr.write('Private metadata collection failed. No data published.\n')
        sys.exit(error.code)
    except Exception:
        sys.exit(22)
