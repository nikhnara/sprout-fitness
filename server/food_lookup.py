"""Normalize an exact barcode result. Never infer missing nutrition."""
import math,re
from urllib.parse import urlparse

def normalize_product(product,code):
    if not isinstance(product,dict) or not isinstance(product.get('product_name'),str) or not product['product_name'].strip():
        raise ValueError('No named product found. Enter its nutrition label instead.')
    nutrients=product.get('nutriments',{})
    def amount(key):
        value=nutrients.get(key+'_100g')
        return value if type(value) in (int,float) and math.isfinite(value) and 0<=value<=1000 else None
    image=product.get('image_front_small_url','')
    if not isinstance(image,str) or urlparse(image).scheme!='https' or urlparse(image).hostname!='images.openfoodfacts.org':image=None
    label=' · '.join(v.strip() for v in [product.get('brands'),product['product_name'],product.get('quantity')] if isinstance(v,str) and v.strip())[:180]
    result={'id':'off-'+code,'name':label, 'displayName':label,
        'source':'Open Food Facts · community product label','sourceUrl':'https://world.openfoodfacts.org/product/'+code,
        'basisGrams':100,'defaultGrams':100,'diet':'other','portions':[],
        'note':'Match the brand, pack and preparation to your label. Community records can be incomplete. Carbohydrate follows the source label; regional definitions may differ. Data: Open Food Facts (ODbL); images: CC BY-SA.',
        'nutrients':{key:amount(off) for key,off in {'kcal':'energy-kcal','protein':'proteins','fat':'fat','carbs':'carbohydrates','fiber':'fiber'}.items()}}
    if image: result['image']=image
    # Records declared per volume cannot safely be treated as grams.
    quantity=product.get('nutrition_data_per','100g')
    if quantity=='100ml':raise ValueError('This label is per 100 ml. Use custom entry with the correct gram conversion.')
    return result
