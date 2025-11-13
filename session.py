from typing import Dict, Any

_STORE: Dict[str, Dict[str, Any]] = {}

class ChatSessionStore:
    def get(self, sid: str, customer_id=None) -> Dict[str, Any]:
        ctx = _STORE.get(sid, {'customer_id': customer_id, 'last_intent': None})
        if customer_id and ctx.get('customer_id') != int(customer_id):
            ctx['customer_id'] = int(customer_id)
        _STORE[sid] = ctx
        return ctx

    def set(self, sid: str, context: Dict[str, Any]):
        _STORE[sid] = context

    def reset(self, sid: str, customer_id=None) -> Dict[str, Any]:
        ctx = {'customer_id': customer_id, 'last_intent': None}
        _STORE[sid] = ctx
        return ctx
