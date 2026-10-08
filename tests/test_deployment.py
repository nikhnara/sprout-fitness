import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('cloud_deploy', Path(__file__).parents[1] / 'scripts/cloud_deploy.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class DeploymentConfigTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(PROJECT_ID='sprout-example', REGION='us-central1', BUCKET_NAME='sprout-example-ui',
                        OWNER_EMAIL='owner@example.com', GOOGLE_CLIENT_ID='123-example.apps.googleusercontent.com',
                        FRONTEND_ORIGIN='https://fitness.example.com', DEPLOY_BRANCH='main',
                        IMAGE_URI='us-central1-docker.pkg.dev/sprout-example/sprout/api:' + 'a' * 40)
    def test_valid_main_configuration(self):
        self.assertEqual(module.config(self.env)['DEPLOY_BRANCH'], 'main')
    def test_fail_closed_before_deployment(self):
        for key, value in [('DEPLOY_BRANCH', 'feature'), ('BUCKET_NAME', ''),
                           ('FRONTEND_ORIGIN', 'https://storage.googleapis.com'),
                           ('FRONTEND_ORIGIN', 'https://fitness.example.com/path'),
                           ('GOOGLE_CLIENT_ID', 'not-an-oauth-client'),
                           ('IMAGE_URI', 'us-central1-docker.pkg.dev/other-project/sprout/api:' + 'a' * 40)]:
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    module.config({**self.env, key: value})
