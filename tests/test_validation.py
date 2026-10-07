import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
from validation import validate_state

def valid():
 return {'version':1,'profile':{'name':'Test','targets':{'kcal':2000,'protein':100,'carbs':250,'fat':65,'fiber':30,'sleep':8,'exercise':30}},'days':{'2026-10-07':{'weight':80,'sleep':8,'exercise':[{'minutes':30}],'meals':[{'name':'Food','grams':100,'nutrients':{'kcal':100,'protein':5,'fat':2,'carbs':10,'fiber':None}}]}},'customFoods':[],'recipes':[]}
class ValidationTests(unittest.TestCase):
 def test_valid(self): self.assertEqual(validate_state(valid())['version'],1)
 def test_bad_weight(self):
  s=valid();s['days']['2026-10-07']['weight']=-1
  with self.assertRaises(ValueError):validate_state(s)
 def test_nonfinite(self):
  s=valid();s['profile']['targets']['protein']=float('nan')
  with self.assertRaises(ValueError):validate_state(s)
 def test_invalid_date(self):
  s=valid();s['days']['2026-02-31']=s['days'].pop('2026-10-07')
  with self.assertRaises(ValueError):validate_state(s)
 def test_missing_macro_remains_unknown(self): self.assertIsNone(validate_state(valid())['days']['2026-10-07']['meals'][0]['nutrients']['fiber'])
if __name__=='__main__':unittest.main()
