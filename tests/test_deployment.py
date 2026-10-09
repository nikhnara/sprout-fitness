import json
import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path
spec = importlib.util.spec_from_file_location('cloud_deploy', Path(__file__).parents[1] / 'scripts/cloud_deploy.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DeploymentConfigTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(PROJECT_ID='sprout-example', REGION='us-central1', BUCKET_NAME='sprout-example-ui',
                        OWNER_EMAIL='owner@example.com', FIREBASE_CONFIG=json.dumps(dict(apiKey='public-test-key',authDomain='sprout-example.firebaseapp.com',projectId='sprout-example',appId='1:123:web:abc')),
                        FRONTEND_ORIGIN='https://fitness.example.com', DEPLOY_BRANCH='main',
                        IMAGE_URI='us-central1-docker.pkg.dev/sprout-example/sprout/api:' + 'a' * 40)
    def test_valid_main_configuration(self):
        self.assertEqual(module.config(self.env)['DEPLOY_BRANCH'], 'main')
    def test_fail_closed_before_deployment(self):
        for key, value in [('DEPLOY_BRANCH', 'feature'), ('BUCKET_NAME', ''),
                           ('FRONTEND_ORIGIN', 'https://storage.googleapis.com'),
                           ('FRONTEND_ORIGIN', 'https://fitness.example.com/path'),
                           ('FIREBASE_CONFIG', '{}'), ('FIREBASE_CONFIG', '{bad json'), ('FIREBASE_CONFIG', json.dumps(dict(private_key='never allowed'))),
                           ('IMAGE_URI', 'us-central1-docker.pkg.dev/other-project/sprout/api:' + 'a' * 40)]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    module.config({**self.env, key: value})

    def test_separate_firebase_project_is_explicitly_preserved(self):
        firebase = json.loads(self.env['FIREBASE_CONFIG'])
        firebase['projectId'] = 'separate-auth-project'
        parsed = module.config({**self.env, 'FIREBASE_CONFIG': json.dumps(firebase)})
        self.assertEqual(parsed['PROJECT_ID'], 'sprout-example')
        self.assertEqual(parsed['firebase']['projectId'], 'separate-auth-project')

    def test_missing_values_name_the_trigger_settings(self):
        with self.assertRaisesRegex(ValueError, r'Missing deployment settings: _BUCKET_NAME, _OWNER_EMAIL'):
            module.config({**self.env, 'BUCKET_NAME': '', 'OWNER_EMAIL': '   '})

    def test_deploy_attaches_the_existing_runtime_accounts(self):
        c = module.config(self.env)
        calls = []
        def fake_run(*args):
            calls.append(args)
            return 'https://example-api.run.app' if args[:4] == ('gcloud', 'run', 'services', 'describe') else ''
        with patch.object(module, 'run', side_effect=fake_run), patch.object(Path, 'write_text'):
            module.deploy(c)
        deploys = [args for args in calls if args[:3] == ('gcloud', 'run', 'deploy')]
        attached = {args[3]: args[args.index('--service-account') + 1] for args in deploys}
        self.assertEqual(attached, {
            'sprout-api': 'gamna-396@sprout-example.iam.gserviceaccount.com',
            'sprout-web': 'sprout-web@sprout-example.iam.gserviceaccount.com'})
