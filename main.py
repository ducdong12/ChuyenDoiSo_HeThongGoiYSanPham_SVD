import sys
import os
from flask import Flask, request, jsonify, render_template
import pandas as pd
import logging

# Cấu hình logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Thêm src vào Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

# SỬA: Đường dẫn templates đúng với cấu trúc hiện tại
static_dir = os.path.join(current_dir, 'static')
templates_dir = os.path.join(static_dir, 'templates')  # GIỮ NGUYÊN như ban đầu

# Import từ các module trong src
try:
    from models.recommender import AdvancedRecommender
    from utils.database import DatabaseManager
    from utils.data_loader import DataLoader
    print("✅ Import modules thành công")
except ImportError as e:
    print(f"❌ Lỗi import: {e}")
    sys.exit(1)

# Khởi tạo Flask với đường dẫn CHÍNH XÁC
app = Flask(__name__,
            template_folder=templates_dir,  # SỬA: Giữ nguyên static/templates
            static_folder=static_dir)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Khởi tạo components
try:
    db = DatabaseManager()
    recommender = AdvancedRecommender()
    data_loader = DataLoader()
    print("✅ Khởi tạo components thành công")
except Exception as e:
    print(f"❌ Lỗi khởi tạo components: {e}")

@app.route('/')
def home():
    """Trang chủ với giao diện tìm kiếm bằng số điện thoại"""
    try:
        # KIỂM TRA TRƯỚC KHI RENDER
        index_path = os.path.join(templates_dir, 'index.html')
        logger.info(f"🔍 Đang tìm template tại: {index_path}")
        
        if not os.path.exists(index_path):
            logger.error(f"❌ File index.html không tồn tại tại: {index_path}")
            # Liệt kê các file trong thư mục templates
            if os.path.exists(templates_dir):
                files = os.listdir(templates_dir)
                logger.info(f"📂 Các file trong templates: {files}")
            else:
                logger.error(f"❌ Thư mục templates không tồn tại: {templates_dir}")
            
            return f"""
            <html>
                <head><title>Lỗi hệ thống</title></head>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h1>⚠️ Lỗi hệ thống</h1>
                    <p><strong>Không thể tìm thấy file index.html</strong></p>
                    <p>Đường dẫn tìm kiếm: <code>{index_path}</code></p>
                    <p>Vui lòng kiểm tra:</p>
                    <ul>
                        <li>File index.html có trong thư mục static/templates/ không?</li>
                        <li>Cấu trúc thư mục có đúng không?</li>
                    </ul>
                    <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
                        <h3>📁 Cấu trúc thư mục mong đợi:</h3>
                        <pre>
BTL-Recommendation-System/
├── main.py
├── static/
│   └── templates/
│       └── index.html    ← File này phải tồn tại
│   └── css/
│   └── js/
└── src/
                        </pre>
                    </div>
                </body>
            </html>
            """
        
        return render_template('index.html')
        
    except Exception as e:
        logger.error(f"Lỗi render template: {e}")
        return f"""
        <html>
            <head><title>Lỗi hệ thống</title></head>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h1>❌ Lỗi hệ thống</h1>
                <p><strong>Không thể tải template:</strong> {e}</p>
                <p><strong>Đường dẫn templates:</strong> {templates_dir}</p>
                <button onclick="window.location.reload()">Thử lại</button>
            </body>
        </html>
        """

# ==================== API ENDPOINTS ====================

@app.route('/api/customer/search', methods=['POST'])
def search_customer():
    """
    Tìm khách hàng bằng số điện thoại.
    - Khi tìm thấy: RESET trạng thái recommender cho khách hàng mới ngay lập tức.
    - FE có thể dựa vào field 'reset': true để clear UI (danh mục gợi ý & gợi ý thông minh).
    Body: { "phone": "0899..." }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        phone_number = data.get('phone')
        logger.info(f"🔍 Tìm kiếm khách hàng với SĐT: {phone_number}")
        
        if not phone_number:
            return jsonify({'error': 'Số điện thoại là bắt buộc'}), 400
        
        # Tìm khách hàng trong database (yêu cầu DatabaseManager có hàm này)
        customer = db.get_customer_by_phone(phone_number)
        
        if customer.empty:
            logger.warning(f"❌ Không tìm thấy khách hàng: {phone_number}")
            return jsonify({
                'success': False,
                'found': False,
                'message': 'Không tìm thấy khách hàng với số điện thoại này'
            }), 404
        
        customer_info = customer.iloc[0].to_dict()
        customer_id = int(customer_info['customer_id'])
        logger.info(f"✅ Tìm thấy khách hàng: {customer_info.get('name', 'N/A')} (ID={customer_id})")

        # Lấy lịch sử mua hàng của khách hàng
        purchase_history = db.get_customer_purchase_history(customer_id)

        # 🔄 RESET recommender state NGAY TẠI ĐÂY
        if hasattr(recommender, "reset_for_new_customer"):
            recommender.reset_for_new_customer(customer_id)
        else:
            # fallback: nếu bạn chưa thêm wrapper, auto-reset vẫn diễn ra khi recommend_products được gọi
            # nhưng chúng ta vẫn lưu customer_id hiện tại để đồng bộ
            recommender._current_customer_id = customer_id
            recommender.user_profiles = {}
            recommender.product_features = {}
            if hasattr(recommender, "_session_recommended_ids"):
                recommender._session_recommended_ids = set()
        logger.info("🔄 Đã reset phiên gợi ý cho khách hàng mới.")

        return jsonify({
            'success': True,
            'found': True,
            'customer': customer_info,
            'purchase_history': purchase_history,
            'reset': True,  # FE dựa vào đây để clear 2 panel gợi ý
            'message': 'Tìm thấy khách hàng thành công'
        })
        
    except Exception as e:
        logger.error(f"Lỗi tìm kiếm khách hàng: {e}")
        return jsonify({
            'success': False,
            'error': f'Lỗi server: {str(e)}'
        }), 500


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Lấy danh sách danh mục sản phẩm"""
    try:
        categories = db.get_categories()
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        logger.error(f"Lỗi lấy danh mục: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'categories': []
        }), 500


@app.route('/api/recommend/manual', methods=['POST'])
def recommend_manual():
    """
    Gợi ý sản phẩm theo danh mục.
    - Nhận customer_id để đảm bảo đúng phiên; nếu khác phiên hiện tại → reset.
    - Loại trừ sản phẩm đã mua.
    Body: { "customer_id": 1, "categories": ["Điện tử"], "n_recommendations": 5 }
    """
    try:
        data = request.get_json() or {}
        customer_id = data.get('customer_id')
        categories = data.get('categories', [])
        n_recommendations = int(data.get('n_recommendations', 5))
        
        logger.info(f"🎯 Gợi ý manual - Customer ID: {customer_id}, Danh mục: {categories}, Số lượng: {n_recommendations}")
        
        if not categories:
            return jsonify({
                'success': False,
                'error': 'Vui lòng chọn ít nhất một danh mục'
            }), 400

        # Nếu không truyền customer_id thì dùng phiên hiện tại (nếu có)
        if not customer_id:
            customer_id = getattr(recommender, "_current_customer_id", None)
        if not customer_id:
            return jsonify({'success': False, 'error': 'Thiếu customer_id'}), 400

        # 🔒 Bảo vệ: đổi khách → reset
        if getattr(recommender, "_current_customer_id", None) != int(customer_id):
            if hasattr(recommender, "reset_for_new_customer"):
                recommender.reset_for_new_customer(int(customer_id))
            else:
                recommender._current_customer_id = int(customer_id)
                recommender.user_profiles = {}
                recommender.product_features = {}
                if hasattr(recommender, "_session_recommended_ids"):
                    recommender._session_recommended_ids = set()
            logger.info("🔄 Manual: đã reset phiên do customer_id thay đổi.")

        # Lấy sản phẩm theo danh mục, loại trừ đã mua
        conn = db.connect()
        try:
            params = [int(customer_id)]
            where_cat = ""
            if categories:
                placeholders = ",".join(["?"] * len(categories))
                where_cat = f" AND p.category IN ({placeholders})"
                params += categories

            sql = f"""
                SELECT p.product_id, p.name, p.category, p.price, p.brand
                FROM products p
                WHERE p.product_id NOT IN (
                    SELECT product_id FROM purchase_history WHERE customer_id = ?
                )
                {where_cat}
                ORDER BY RANDOM()
                LIMIT {n_recommendations}
            """
            df = pd.read_sql(sql, conn, params=params)

            recs = []
            for _, r in df.iterrows():
                recs.append({
                    "product_id": int(r["product_id"]),
                    "name": r["name"],
                    "category": r["category"],
                    "price": float(r["price"]),
                    "brand": r["brand"],
                    "score": 0.7,
                    "reason": "Gợi ý theo danh mục đã chọn"
                })

            return jsonify({"success": True, "recommendations": recs, "count": len(recs)})

        finally:
            conn.close()
        
    except Exception as e:
        logger.error(f"Lỗi gợi ý manual: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/recommend/smart_fallback', methods=['POST'])
def recommend_smart_fallback():
    """Gợi ý dự phòng khi smart recommendation thất bại"""
    try:
        data = request.get_json() or {}
        customer_id = data.get('customer_id')
        n_recommendations = int(data.get('n_recommendations', 5))
        
        logger.info(f"🔄 Gợi ý fallback - Customer ID: {customer_id}")
        
        recommendations = recommender.get_diverse_popular_products(n_recommendations)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations),
            'type': 'fallback'
        })
        
    except Exception as e:
        logger.error(f"Lỗi gợi ý fallback: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Kiểm tra tình trạng hệ thống"""
    try:
        categories = db.get_categories()
        index_path = os.path.join(templates_dir, 'index.html')
        template_exists = os.path.exists(index_path)
        
        return jsonify({
            'status': 'healthy' if template_exists else 'degraded',
            'database': 'connected',
            'template': 'found' if template_exists else 'missing',
            'template_path': index_path,
            'categories_count': len(categories),
            'templates_directory': templates_dir
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
    

@app.route('/api/recommend/smart', methods=['POST'])
def recommend_smart():
    """
    Gợi ý thông minh dựa trên lịch sử mua hàng.
    - Nhận customer_id; nếu khác phiên hiện tại → reset trước khi recommend.
    - Hỗ trợ chọn thuật toán: { "algorithm": "hybrid" | "content" | "collaborative" | "svd" }
    Body: { "customer_id": 1, "n_recommendations": 5, "algorithm": "hybrid" }
    """
    try:
        data = request.get_json() or {}
        customer_id = data.get('customer_id')
        n_recommendations = int(data.get('n_recommendations', 5))
        algorithm = data.get('algorithm') or 'hybrid'
        
        logger.info(f"🧠 Gợi ý smart - Customer ID: {customer_id}, Số lượng: {n_recommendations}, Algo: {algorithm}")
        
        if not customer_id:
            # fallback: dùng phiên hiện tại nếu có
            customer_id = getattr(recommender, "_current_customer_id", None)

        if not customer_id:
            return jsonify({'success': False, 'error': 'Thiếu customer_id'}), 400

        # 🔒 Bảo vệ: đổi khách → reset
        if getattr(recommender, "_current_customer_id", None) != int(customer_id):
            if hasattr(recommender, "reset_for_new_customer"):
                recommender.reset_for_new_customer(int(customer_id))
            else:
                recommender._current_customer_id = int(customer_id)
                recommender.user_profiles = {}
                recommender.product_features = {}
                if hasattr(recommender, "_session_recommended_ids"):
                    recommender._session_recommended_ids = set()
            logger.info("🔄 Smart: đã reset phiên do customer_id thay đổi.")

        recommendations = recommender.recommend_products(
            customer_id=int(customer_id),
            n_recommendations=n_recommendations,
            algorithm=algorithm
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'count': len(recommendations)
        })
        
    except Exception as e:
        logger.error(f"Lỗi gợi ý smart: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# (Tuỳ chọn) API reset thủ công, dùng khi cần
@app.route('/api/session/reset', methods=['POST'])
def reset_session():
    """
    Body: { "customer_id": 1 }
    Cho phép FE reset phiên recommender một cách tường minh.
    """
    try:
        data = request.get_json() or {}
        customer_id = data.get('customer_id')
        if not customer_id:
            return jsonify({'success': False, 'error': 'Thiếu customer_id'}), 400

        if hasattr(recommender, "reset_for_new_customer"):
            recommender.reset_for_new_customer(int(customer_id))
        else:
            recommender._current_customer_id = int(customer_id)
            recommender.user_profiles = {}
            recommender.product_features = {}
            if hasattr(recommender, "_session_recommended_ids"):
                recommender._session_recommended_ids = set()

        return jsonify({'success': True, 'reset': True})
    except Exception as e:
        logger.error(f"Lỗi reset session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Body:
    {
      "message": "tôi muốn mua đồ điện tử",
      "customer_id": 1,               # optional
      "session_id": "web-abc123",     # optional (FE sinh)
      "metadata": {"channel":"web"}   # optional
    }
    """
    try:
        data = request.get_json() or {}
        text = (data.get('message') or '').strip()
        if not text:
            return jsonify({'success': False, 'error': 'Thiếu message'}), 400

        cid = data.get('customer_id')
        sid = data.get('session_id') or f"sid_{request.remote_addr}"

        # === NLU ===
        from bot.nlu import detect_intent_entities
        nlu = detect_intent_entities(text, known_categories=db.get_categories())

        # === Session context ===
        from bot.session import ChatSessionStore
        store = ChatSessionStore()
        context = store.get(sid, cid)
        if cid and (context.get('customer_id') != int(cid)):
            context = store.reset(sid, customer_id=int(cid))

        # === Dialog manager ===
        from bot.dialog import handle_turn
        reply, context_upd, suggestions = handle_turn(
            text=text,
            nlu=nlu,
            context=context,
            db=db,
            recommender=recommender
        )

        store.set(sid, context_upd)

        return jsonify({
            'success': True,
            'reply': reply,
            'suggestions': suggestions,
            'nlu': nlu,            # có thể tắt khi production
            'context': context_upd # có thể tắt khi production
        })
    except Exception as e:
        logger.exception("Chat error")
        return jsonify({'success': False, 'error': str(e)}), 500



if __name__ == '__main__':
    print("🚀 Starting Smart Product Recommendation System...")
    print(f"📁 Current directory: {current_dir}")
    print(f"📁 Static directory: {static_dir}")
    print(f"📁 Templates directory: {templates_dir}")
    
    # Kiểm tra hệ thống chi tiết
    print("\n🔍 Kiểm tra hệ thống chi tiết...")
    
    # Kiểm tra templates
    index_path = os.path.join(templates_dir, 'index.html')
    if os.path.exists(templates_dir):
        print("✅ Thư mục templates tồn tại")
        if os.path.exists(index_path):
            print("✅ index.html tồn tại")
        else:
            print("❌ index.html KHÔNG tồn tại")
            print(f"   Đường dẫn: {index_path}")
            files = os.listdir(templates_dir)
            print(f"   Các file trong templates: {files}")
    else:
        print("❌ Thư mục templates KHÔNG tồn tại")
        print(f"   Đường dẫn: {templates_dir}")
    
    # Kiểm tra database
    try:
        db.create_tables()
        db.insert_sample_data()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    print("\n🌐 Starting Flask server...")
    print("🔧 Available APIs:")
    print("   GET  /api/health - Kiểm tra hệ thống")
    print("   POST /api/customer/search - Tìm khách hàng bằng SĐT (có reset)")
    print("   GET  /api/categories - Lấy danh sách danh mục")
    print("   POST /api/recommend/manual - Gợi ý theo danh mục (auto-reset nếu đổi khách)")
    print("   POST /api/recommend/smart - Gợi ý thông minh (auto-reset nếu đổi khách)")
    print("   POST /api/session/reset - Reset phiên recommender (tuỳ chọn)")
    print("\n📞 Test với SĐT mẫu: 0899590556")
    print("✅ System ready! Open: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
