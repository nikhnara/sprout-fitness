"""Idempotent reporting schema and validated public catalog release. No diary rewrites."""
import argparse,json,re,subprocess
from pathlib import Path

def migrate(project):
 if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',project):raise ValueError('Invalid project')
 metadata=json.loads(subprocess.check_output(['bq','--project_id='+project,'show','--format=json',project+':fitness'],text=True))
 location=metadata['location']
 if not re.fullmatch(r'[A-Za-z0-9-]+',location):raise ValueError('Invalid dataset location')
 def bq(*args):subprocess.run(['bq','--project_id='+project,'--location='+location,*args],check=True)
 def query(sql):subprocess.run(['bq','--project_id='+project,'--location='+location,'query','--use_legacy_sql=false'],input=sql,text=True,check=True)
 schema=Path('server/schema.sql').read_text().replace('YOUR_PROJECT_ID',project)
 schema='\n'.join(line for line in schema.splitlines() if not line.startswith('CREATE SCHEMA'))
 query(schema)
 sql=Path('server/catalog_schema.sql').read_text().replace('YOUR_PROJECT_ID',project)
 tables,views=sql.split('CREATE OR REPLACE VIEW',1)
 query(tables)
 for table,path,fields in [
 ('food_sources','data/sources.ndjson','source_id:STRING,name:STRING,url:STRING,release_date:DATE'),
 ('food_catalog','data/catalog.ndjson','food_id:STRING,source_id:STRING,name:STRING,canonical_name:STRING,diet:STRING,category:STRING,basis_grams:FLOAT,estimated:BOOLEAN,record:JSON')]:
  bq('load','--replace','--source_format=NEWLINE_DELIMITED_JSON',project+':fitness.'+table,path,fields)
 query('CREATE OR REPLACE VIEW'+views)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',required=True);migrate(p.parse_args().project)
