import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'server'))
from food_lookup import normalize_product
class ProductTests(unittest.TestCase):
 def test_unknowns_and_untrusted_images(self):
  f=normalize_product({'product_name':'Yogurt','image_front_small_url':'https://evil.test/track','nutriments':{'proteins_100g':20,'fiber_100g':None}},'12345678')
  self.assertEqual(f['nutrients']['protein'],20);self.assertIsNone(f['nutrients']['fiber']);self.assertNotIn('image',f)
 def test_volume_does_not_silently_become_mass(self):
  with self.assertRaises(ValueError):normalize_product({'product_name':'Milk','nutrition_data_per':'100ml'},'12345678')
