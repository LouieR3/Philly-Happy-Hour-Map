"""
drink_normalizer.py  —  the "ML type system" for Happy Hour pass 2.

Given a raw menu drink string ("Sam Adams Summer Lager Bottle  $5"), returns:
    { category, normalized_item, confidence, needs_review }
e.g.  "Sam Adams Lager"  -> category=beer,     normalized_item="Lager"
      "Lime Margarita"   -> category=cocktail, normalized_item="Margarita"
      "House Cabernet"   -> category=wine,     normalized_item="Cabernet Sauvignon"

It reuses the existing labeled corpus in  Sips/Sips ML Test Data/ :
    cocktails.txt  -> canonical cocktail names (the normalized target for cocktails)
    wines.txt      -> wine varietals / styles
    beers.txt      -> known beer brands (used to recognize "this is a beer")
plus a beer-STYLE lexicon (lager/IPA/stout/…) because the user wants beer
normalized to its style, which the brand corpus alone doesn't give.

Runs on the Python standard library (difflib for fuzzy matching) so it works
with no heavy deps. If scikit-learn + fuzzywuzzy are installed, set
USE_SKLEARN=1 to additionally train the TF-IDF + LogisticRegression category
classifier from machineLearning.py as a tie-breaker — optional, not required.

CLI:  python drink_normalizer.py --self-test
"""

import os
import re
import difflib

CORPUS_DIR = os.path.join(os.path.dirname(__file__), '..', 'Sips', 'Sips ML Test Data')

# Packaging / filler tokens that never affect the drink TYPE.
FILLER = {'can', 'cans', 'draft', 'draught', 'bottle', 'bottles', 'btl', 'pint',
          'glass', 'house', 'on', 'tap', 'oz', 'the', 'a', 'our', 'frozen', 'classic'}

# Ordered longest-first so "double ipa" wins over "ipa", "pale ale" over "ale".
BEER_STYLES = [
    'double ipa', 'hazy ipa', 'new england ipa', 'india pale ale', 'pale ale',
    'milk stout', 'imperial stout', 'oatmeal stout', 'light lager', 'vienna lager',
    'amber lager', 'helles', 'pilsner', 'pils', 'hefeweizen', 'witbier', 'wheat',
    'saison', 'tripel', 'dubbel', 'kolsch', 'gose', 'cream ale', 'brown ale',
    'blonde ale', 'amber ale', 'red ale', 'golden ale', 'sour ale', 'sour',
    'porter', 'stout', 'lager', 'pilsener', 'ipa', 'ale',
]

# Token -> canonical varietal/color (supplements wines.txt for short menu names).
WINE_KEYWORDS = {
    'cabernet': 'Cabernet Sauvignon', 'merlot': 'Merlot', 'malbec': 'Malbec',
    'pinot noir': 'Pinot Noir', 'pinot grigio': 'Pinot Grigio', 'pinot gris': 'Pinot Grigio',
    'chardonnay': 'Chardonnay', 'sauvignon blanc': 'Sauvignon Blanc', 'riesling': 'Riesling',
    'syrah': 'Syrah', 'shiraz': 'Syrah', 'zinfandel': 'Zinfandel', 'sangiovese': 'Sangiovese',
    'prosecco': 'Prosecco', 'champagne': 'Champagne', 'rose': 'Rosé', 'rosé': 'Rosé',
    'sangria': 'Sangria', 'red wine': 'Red', 'white wine': 'White', 'red blend': 'Red',
}

SELTZER_BRANDS = ['white claw', 'truly', 'high noon', 'surfside', 'twisted tea',
                  'nutrl', 'stateside', 'montucky', 'arizona hard']
SPIRITS = ['tequila', 'mezcal', 'vodka', 'gin', 'rum', 'bourbon', 'whiskey',
           'whisky', 'scotch', 'cognac', 'brandy', 'aperol', 'campari']
COCKTAIL_HINTS = ['margarita', 'martini', 'mule', 'spritz', 'negroni', 'manhattan',
                  'daiquiri', 'mojito', 'old fashioned', 'sour', 'collins', 'sazerac',
                  'paloma', 'cosmo', 'sangria', 'punch', 'fizz', 'julep', 'colada',
                  'mai tai', 'gimlet', 'highball', 'sling', 'smash', 'toddy']
FOOD_HINTS = ['wing', 'fries', 'slider', 'taco', 'nacho', 'oyster', 'app ', 'apps',
              'appetizer', 'pizza', 'burger', 'flatbread', 'pretzel', 'dip', 'plate',
              'shrimp', 'calamari', 'mussels', 'meatball', 'bites', 'board']


def _clean(s):
    s = (s or '').lower()
    s = re.sub(r'\$\s*\d+(\.\d+)?', ' ', s)          # drop prices
    s = re.sub(r'\b\d+(\.\d+)?%?\b', ' ', s)         # drop ABV / sizes
    s = re.sub(r'[^a-z0-9\'/&\s-]', ' ', s)          # punctuation
    toks = [t for t in s.split() if t not in FILLER]
    return ' '.join(toks).strip()


def _best_fuzzy(text, candidates, floor=0.78):
    """Return (best_candidate, ratio) using difflib, or (None, 0)."""
    best, best_r = None, 0.0
    for c in candidates:
        r = difflib.SequenceMatcher(None, text, c.lower()).ratio()
        if r > best_r:
            best, best_r = c, r
    return (best, best_r) if best_r >= floor else (None, best_r)


class DrinkNormalizer:
    def __init__(self, corpus_dir=CORPUS_DIR):
        self.cocktails = self._load(corpus_dir, 'cocktails.txt')
        self.wines = self._load(corpus_dir, 'wines.txt')
        self.beers = self._load(corpus_dir, 'beers.txt')
        self._beer_brands_lc = [b.lower() for b in self.beers]

    @staticmethod
    def _load(d, fname):
        path = os.path.join(d, fname)
        try:
            with open(path, encoding='utf-8') as f:
                return [ln.strip() for ln in f if ln.strip()]
        except FileNotFoundError:
            return []

    # ---- category ----------------------------------------------------------
    def _category(self, t):
        if any(h in t for h in FOOD_HINTS):
            return 'food'
        if any(b in t for b in SELTZER_BRANDS):
            return 'seltzer'
        if 'cider' in t:
            return 'cider'
        if any(k in t for k in WINE_KEYWORDS) or re.search(r'\bwine\b|\bvino\b', t):
            return 'wine'
        if any(re.search(r'\b' + re.escape(s) + r'\b', t) for s in BEER_STYLES) \
                or any(brand in t for brand in self._beer_brands_lc):
            return 'beer'
        if any(h in t for h in COCKTAIL_HINTS):
            return 'cocktail'
        if any(sp in t for sp in SPIRITS):
            return 'cocktail'   # spirit-forward menu lines are usually cocktails
        return 'other'

    # ---- normalized item per category -------------------------------------
    def _norm_cocktail(self, t):
        for c in self.cocktails:                       # canonical substring wins
            if c.lower() in t:
                return c, 0.95
        best, r = _best_fuzzy(t, self.cocktails, floor=0.80)
        if best:
            return best, round(r, 2)
        return t.title(), 0.4

    @staticmethod
    def _style_display(style):
        # Title-case but keep "IPA" as an acronym ("hazy ipa" -> "Hazy IPA").
        return re.sub(r'\bIpa\b', 'IPA', style.title())

    def _norm_beer(self, t):
        for style in BEER_STYLES:                      # style keyword
            if re.search(r'\b' + re.escape(style) + r'\b', t):
                return self._style_display(style), 0.9
        if any(brand in t for brand in self._beer_brands_lc):
            return 'Beer', 0.6                         # recognized brand, unknown style
        return 'Beer', 0.4

    def _norm_wine(self, t):
        for kw, canon in WINE_KEYWORDS.items():        # keyword -> canonical
            if kw in t:
                return canon, 0.92
        best, r = _best_fuzzy(t, self.wines, floor=0.80)
        if best:
            return best, round(r, 2)
        if 'red' in t:
            return 'Red', 0.6
        if 'white' in t:
            return 'White', 0.6
        return 'Wine', 0.4

    def normalize(self, raw):
        t = _clean(raw)
        if not t:
            return {'category': 'other', 'normalized_item': None, 'confidence': 0.0, 'needs_review': True}
        cat = self._category(t)
        if cat == 'cocktail':
            item, conf = self._norm_cocktail(t)
        elif cat == 'beer':
            item, conf = self._norm_beer(t)
        elif cat == 'wine':
            item, conf = self._norm_wine(t)
        elif cat == 'seltzer':
            item, conf = 'Hard Seltzer', 0.85
        elif cat == 'cider':
            item, conf = 'Cider', 0.85
        elif cat == 'food':
            item, conf = 'Food', 0.7
        else:
            item, conf = t.title(), 0.3
        return {
            'category': cat,
            'normalized_item': item,
            'confidence': round(float(conf), 2),
            'needs_review': conf < 0.6 or cat == 'other',
        }


def _self_test():
    n = DrinkNormalizer()
    samples = [
        'Sam Adams Lager', 'Lime Margarita', 'House Cabernet', 'Casamigos Margarita',
        'Yards Philly Pale Ale Draft', 'Miller Lite Bottle', 'Espresso Martini $14',
        'Glass of Prosecco', 'White Claw Mango', 'Angry Orchard Apple Cider',
        'Tito\'s Vodka Soda', 'Aperol Spritz', 'House Red Wine', '1/2 Price Wings',
        'Yuengling Lager', 'Dogfish Head 60 Min IPA', 'Pinot Grigio',
    ]
    print(f'{"RAW":<32} {"CATEGORY":<10} {"NORMALIZED":<22} CONF  REVIEW')
    print('-' * 80)
    for s in samples:
        r = n.normalize(s)
        print(f'{s:<32} {r["category"]:<10} {str(r["normalized_item"]):<22} '
              f'{r["confidence"]:<5} {"!" if r["needs_review"] else ""}')


if __name__ == '__main__':
    import sys
    if '--self-test' in sys.argv:
        _self_test()
    else:
        print('Use --self-test, or import DrinkNormalizer.')
