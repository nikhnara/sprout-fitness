import importlib.util,unittest
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('catalog_migration',Path(__file__).resolve().parents[1]/'scripts/migrate_catalog.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CatalogReleaseTests(unittest.TestCase):
 def test_queries_use_stdin_and_do_not_create_unrelated_datasets(self):
  with patch.object(m.subprocess,'check_output',return_value='{"location":"us-central1"}'), patch.object(m.subprocess,'run') as run:
   m.migrate('sprout-fitness')
  queries=[c for c in run.call_args_list if 'query' in c.args[0]]
  self.assertEqual(len(queries),3)
  for q in queries:
   self.assertIsInstance(q.kwargs['input'],str)
   self.assertNotIn('CREATE SCHEMA',q.kwargs['input'])
   self.assertEqual(q.args[0][-1],'--use_legacy_sql=false')
   self.assertIn('--location=us-central1',q.args[0])
 def test_rejects_invalid_project_before_any_command(self):
  with self.assertRaises(ValueError):m.migrate('not a project')
