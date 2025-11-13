import re
from typing import Dict, Any, List

PHONE_RE = re.compile(r'(0|\+?84)(\d{9,10})\b')
NUM_RE = re.compile(r'\b(\d{1,2})\b', re.UNICODE)

BASIC_INTENTS = {
    'greeting':  ['xin chào', 'chào', 'hello', 'hi'],
    'goodbye':   ['tạm biệt', 'bye', 'hẹn gặp'],
    'help':      ['hỗ trợ', 'giúp', 'help', 'hướng dẫn'],
    'search_customer': ['tìm khách', 'tìm sđt', 'tìm số', 'khách hàng'],
    'recommend_smart': ['gợi ý thông minh', 'gợi ý smart', 'đề xuất thông minh'],
    'recommend_manual': ['gợi ý theo danh mục', 'gợi ý danh mục', 'theo danh mục'],
    'product_query': ['sản phẩm', 'mặt hàng', 'giá', 'thương hiệu', 'brand', 'bao nhiêu'],
}

def _contains_any(text: str, keywords: List[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)

def detect_intent_entities(text: str, known_categories: List[str]) -> Dict[str, Any]:
    """
    Kết quả:
    {
      'intent': 'recommend_manual' | 'recommend_smart' | 'search_customer' | 'product_query' | 'chitchat',
      'entities': { 'phone': '0899...', 'categories': [...], 'limit': 5 }
    }
    """
    t = (text or '').strip().lower()
    intent = 'chitchat'
    for k, kws in BASIC_INTENTS.items():
        if _contains_any(t, kws):
            intent = k
            break

    # categories
    categories = []
    if known_categories:
        for c in known_categories:
            if c and c.lower() in t:
                categories.append(c)

    # phone
    phone = None
    m = PHONE_RE.search(text.replace(' ', ''))
    if m:
        phone = m.group(0)

    # limit (số lượng)
    limit = None
    nums = NUM_RE.findall(t)
    if nums:
        try:
            n = int(nums[-1])
            if 1 <= n <= 50:
                limit = n
        except:
            pass

    if categories and intent == 'chitchat':
        intent = 'recommend_manual'

    if intent == 'chitchat' and any(w in t for w in ['giá', 'bao nhiêu', 'chi tiết', 'brand', 'thương hiệu']):
        intent = 'product_query'

    return {
        'intent': intent,
        'entities': {
            'phone': phone,
            'categories': sorted(set(categories)),
            'limit': limit
        }
    }
