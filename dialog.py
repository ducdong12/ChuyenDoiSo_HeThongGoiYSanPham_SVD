from typing import Tuple, Dict, Any, List

def _quick(*labels) -> List[str]:
    return list(labels)

def _ensure_customer(context):
    cid = context.get('customer_id')
    if not cid:
        return False, "Mình chưa biết bạn là khách nào. Bạn gửi số điện thoại (vd: 0899xxxxxx) nhé?", _quick("Tôi muốn nhập số điện thoại")
    return True, None, []

def handle_turn(text: str, nlu: Dict[str, Any], context: Dict[str, Any], db, recommender) -> Tuple[str, Dict[str, Any], List[str]]:
    intent = nlu.get('intent', 'chitchat')
    ents = nlu.get('entities', {})
    context = dict(context or {})
    context['last_intent'] = intent

    # Người dùng gửi SĐT → xác nhận & reset recommender
    if ents.get('phone'):
        phone_raw = ents['phone']
        try:
            cust = db.get_customer_by_phone(phone_raw)
            if not cust.empty:
                cid = int(cust.iloc[0]['customer_id'])
                context['customer_id'] = cid
                if hasattr(recommender, "reset_for_new_customer"):
                    recommender.reset_for_new_customer(cid)
                name = cust.iloc[0].get('name', 'khách hàng')
                return (f"Đã xác nhận SĐT {phone_raw}. Xin chào {name}! "
                        f"Bạn muốn mình hỗ trợ gì?"), context, _quick("Gợi ý thông minh", "Gợi ý theo danh mục", "Xem lịch sử mua")
            else:
                return f"Mình không tìm thấy khách {phone_raw}. Bạn kiểm tra lại giúp nhé.", context, _quick("Nhập lại số điện thoại")
        except Exception as e:
            return f"Tra cứu SĐT gặp lỗi: {e}", context, _quick("Nhập lại số điện thoại")

    # Ý định cơ bản
    if intent in ('greeting', 'help'):
        return ("Chào bạn! Mình có thể: tra cứu khách theo SĐT, gợi ý sản phẩm thông minh, "
                "hoặc gợi ý theo danh mục. Bạn muốn làm gì trước?"), context, _quick("Tôi muốn nhập số điện thoại", "Gợi ý thông minh")

    if intent == 'search_customer':
        return "Bạn gửi mình số điện thoại (vd: 0899xxxxxx) để mình tìm khách hàng nhé.", context, []

    if intent == 'recommend_smart':
        ok, msg, sug = _ensure_customer(context)
        if not ok: return msg, context, sug
        limit = ents.get('limit') or 5
        cid = context['customer_id']
        recs = recommender.recommend_products(customer_id=cid, n_recommendations=limit, algorithm='hybrid')
        if not recs:
            return "Chưa có gợi ý phù hợp. Bạn thử chọn danh mục ưa thích?", context, _quick("Điện tử", "Thời trang", "Thực phẩm")
        lines = ["Dưới đây là gợi ý nổi bật:"]
        for r in recs[:limit]:
            lines.append(f"• {r['name']} ({r['category']}) – {r['price']:,.0f}đ — {r.get('reason','')}")
        return "\n".join(lines), context, _quick("Xem thêm", "Gợi ý theo danh mục")

    if intent == 'recommend_manual':
        ok, msg, sug = _ensure_customer(context)
        if not ok: return msg, context, sug
        cats = ents.get('categories') or []
        if not cats:
            cats_all = db.get_categories()
            return "Bạn muốn gợi ý theo danh mục nào? (bạn có thể gõ tên danh mục)", context, cats_all[:6]
        # lấy nhanh theo danh mục
        conn = db.connect()
        try:
            import pandas as pd
            placeholders = ",".join(["?"] * len(cats))
            sql = f"""
                SELECT p.product_id, p.name, p.category, p.price, p.brand
                FROM products p
                WHERE p.category IN ({placeholders})
                ORDER BY p.product_id DESC
                LIMIT 5
            """
            df = pd.read_sql(sql, conn, params=cats)
            if df.empty:
                return f"Chưa có sản phẩm trong các danh mục {', '.join(cats)}.", context, _quick("Chọn danh mục khác", "Gợi ý thông minh")
            lines = [f"Mình chọn nhanh theo danh mục {', '.join(cats)}:"]
            for _, r in df.iterrows():
                lines.append(f"• {r['name']} ({r['brand']}) – {r['price']:,.0f}đ")
            return "\n".join(lines), context, _quick("Gợi ý thông minh", "Xem thêm")
        finally:
            conn.close()

    if intent == 'product_query':
        # tra cứu theo brand/category đơn giản
        conn = db.connect()
        try:
            import pandas as pd
            q = (text or '').lower()
            cats = db.get_categories()
            found_cats = [c for c in cats if c and c.lower() in q]
            brand = None
            for token in ['brand', 'thương hiệu']:
                if token in q:
                    parts = q.split(token, 1)[1].strip().split()
                    if parts:
                        brand = parts[0]
                        break
            sql = "SELECT name, category, brand, price FROM products WHERE 1=1"
            params = []
            if found_cats:
                sql += " AND category IN ({})".format(",".join(["?"]*len(found_cats)))
                params += found_cats
            if brand:
                sql += " AND lower(brand) = ?"
                params.append(brand.lower())
            sql += " ORDER BY price ASC LIMIT 5"
            df = pd.read_sql(sql, conn, params=params)
            if df.empty:
                return "Mình chưa tìm thấy sản phẩm khớp mô tả. Bạn có thể cho mình biết danh mục hoặc thương hiệu cụ thể hơn không?", context, _quick("Điện tử", "Thời trang", "Thực phẩm")
            lines = ["Mình thấy các sản phẩm liên quan:"]
            for _, r in df.iterrows():
                lines.append(f"• {r['name']} – {r['brand']} – {r['category']} – {r['price']:,.0f}đ")
            return "\n".join(lines), context, _quick("Gợi ý thông minh", "Xem thêm")
        except Exception as e:
            return f"Không tra cứu được sản phẩm vì lỗi: {e}", context, _quick("Gợi ý thông minh")
        finally:
            conn.close()

    if intent == 'goodbye':
        return "Cảm ơn bạn đã trò chuyện. Hẹn gặp lại! 👋", context, []

    return "Mình chưa hiểu rõ. Bạn muốn gợi ý thông minh hay gợi ý theo danh mục?", context, _quick("Gợi ý thông minh", "Gợi ý theo danh mục", "Tôi muốn nhập số điện thoại")
