import copy,json,subprocess,sys,unittest,pathlib
from collect_private import merge,CollectionFailure,QUERY

BASE={'schema_version':3,'account_id':145811541,'repositories':[], 'contribution_history': {'observed_on':'2026-11-01','days':[]},'language_colors':{}}
def response(nodes,more=False,cursor=None,owner='azdeenzack'):
 return {'data':{'viewer':{'login':owner,'repositories':{'nodes':nodes,'pageInfo':{'hasNextPage':more,'endCursor':cursor}}}}}
def node(rid=1,visibility='PRIVATE'):
 return {'databaseId':rid,'visibility':visibility,'isFork':False,'primaryLanguage':{'name':'Python','color':'#3572A5'}}
class Tests(unittest.TestCase):
 def test_merge(self):
  b=copy.deepcopy(BASE);out=merge(b,lambda _:response([node()]));self.assertEqual(b,BASE);self.assertEqual(out['repositories'][0]['visibility'],'private');self.assertEqual(out['language_colors'],{'Python':'#3572a5'})
 def test_matching_color_case_is_normalized(self):
  b=copy.deepcopy(BASE);b['language_colors']={'Python':'#3572a5'}
  out=merge(b,lambda _:response([node()]));self.assertEqual(out['language_colors']['Python'],'#3572a5')
 def test_conflicting_color_still_rejected(self):
  b=copy.deepcopy(BASE);b['language_colors']={'Python':'#000000'}
  with self.assertRaises(CollectionFailure):merge(b,lambda _:response([node()]))
 def test_pagination(self):
  out=merge(BASE,lambda c:response([node(1)],True,'next') if c is None else response([node(2)]));self.assertEqual(len(out['repositories']),2)
 def test_wrong_owner(self):
  with self.assertRaises(CollectionFailure):merge(BASE,lambda _:response([node()],owner='other'))
 def test_wrong_visibility(self):
  with self.assertRaises(CollectionFailure):merge(BASE,lambda _:response([node(visibility='INTERNAL')]))
 def test_duplicate(self):
  with self.assertRaises(CollectionFailure):merge(BASE,lambda _:response([node(),node()]))
 def test_cursor_loop(self):
  with self.assertRaises(CollectionFailure):merge(BASE,lambda _:response([],True,'same'))
 def test_error(self):
  with self.assertRaises(CollectionFailure):merge(BASE,lambda _:{'errors':[{'message':'SECRET_REPO_NAME'}]})
 def test_no_names_query(self):
  self.assertNotIn('nameWithOwner',QUERY);self.assertNotIn('description',QUERY);self.assertNotIn('object(',QUERY);self.assertIn('ownerAffiliations:[OWNER]',QUERY)
 def test_no_secret_in_error(self):
  p=subprocess.run([sys.executable,str(pathlib.Path(__file__).with_name('collect_private.py'))],capture_output=True,text=True,env={'KOI_PRIVATE_METADATA_TOKEN':'TEST_SECRET_NOT_REAL'})
  self.assertEqual(p.returncode,40);self.assertEqual(p.stdout,'');self.assertEqual(p.stderr,'Private metadata collection failed. No data published.\n')
if __name__=='__main__':unittest.main()
