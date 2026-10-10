"""Idempotent reporting schema and validated public catalog release. No diary rewrites."""
import argparse,json,re,subprocess
from pathlib import Path

def migrate(project):
 if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',project):raise ValueError('Invalid project')
 def bq(*args):subprocess.run(['bq','--project_id='+project,'--location=US',*args],check=True)
 schema=Path('server/schema.sql').read_text().replace('YOUR_PROJECT_ID',project)
 bq('query','--use_legacy_sql=false',schema)
 sql=Path('server/catalog_schema.sql').read_text().replace('YOUR_PROJECT_ID',project)
 tables,views=sql.split('CREATE OR REPLACE VIEW',1)
 bq('query','--use_legacy_sql=false',tables)
 for table,path,fields in [
 ('food_sources','data/sources.ndjson','source_id:STRING,name:STRING,url:STRING,release_date:DATE'),
 ('food_catalog','data/catalog.ndjson','food_id:STRING,source_id:STRING,name:STRING,canonical_name:STRING,diet:STRING,category:STRING,basis_grams:FLOAT,estimated:BOOLEAN,record:JSON')]:
  bq('load','--replace','--source_format=NEWLINE_DELIMITED_JSON',project+':fitness.'+table,path,fields)
 bq('query','--use_legacy_sql=false','CREATE OR REPLACE VIEW'+views)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',required=True);migrate(p.parse_args().project)
