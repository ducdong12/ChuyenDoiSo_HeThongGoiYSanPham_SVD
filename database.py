import sqlite3
import pandas as pd
import os

class DatabaseManager:
    def __init__(self):
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.db_path = os.path.join(current_dir, "data", "supermarket.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def connect(self):
        return sqlite3.connect(self.db_path)
    
    def create_tables(self):
        conn = self.connect()
        cursor = conn.cursor()
        
        # Xóa các bảng cũ nếu tồn tại
        cursor.execute("DROP TABLE IF EXISTS purchase_history")
        cursor.execute("DROP TABLE IF EXISTS products")
        cursor.execute("DROP TABLE IF EXISTS customers")
        
        # Tạo lại các bảng
        cursor.execute("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                price REAL,
                brand TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE purchase_history (
                purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                product_id INTEGER,
                quantity INTEGER DEFAULT 1,
                rating INTEGER DEFAULT 5,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Đã tạo các bảng database thành công!")
    
    def insert_sample_data(self):
        """Thêm dữ liệu mẫu để test"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Thêm khách hàng mẫu - CẬP NHẬT SỐ ĐIỆN THOẠI THÀNH "0899590556"
        customers = [
            ("Nguyễn Văn An", "0899590556", "an.nguyen@email.com"),
            ("Trần Thị Bình", "0923456789", "binh.tran@email.com"),
            ("Lê Văn Cường", "0934567890", "cuong.le@email.com"),
            ("Phạm Thị Dung", "0945678901", "dung.pham@email.com"),
            ("Hoàng Văn Em", "0956789012", "em.hoang@email.com"),
            ("Nguyễn Thị Lan", "0967890123", "lan.nguyen@email.com"),
            ("Trần Văn Hùng", "0978901234", "hung.tran@email.com"),
            ("Lê Thị Mai", "0989012345", "mai.le@email.com"),
            ("Phạm Văn Nam", "0990123456", "nam.pham@email.com"),
            ("Hoàng Thị Oanh", "0901234567", "oanh.hoang@email.com")
        ]
        
        cursor.executemany(
            "INSERT INTO customers (name, phone, email) VALUES (?, ?, ?)",
            customers
        )
        
        # Thêm sản phẩm mẫu với NHIỀU DANH MỤC ĐA DẠNG
        products = [
            # Thực phẩm
            ("Sữa Vinamilk", "Thực phẩm", 25000, "Vinamilk"),
            ("Bánh Oreo", "Thực phẩm", 15000, "Oreo"),
            ("Cà phê G7", "Thực phẩm", 50000, "G7"),
            ("Nước suối Lavie", "Thực phẩm", 8000, "Lavie"),
            ("Mì tôm Hảo Hảo", "Thực phẩm", 3500, "Hảo Hảo"),
            ("Kem Merino", "Thực phẩm", 12000, "Merino"),
            ("Chocolate Dove", "Thực phẩm", 45000, "Dove"),
            ("Trà Lipton", "Thực phẩm", 20000, "Lipton"),
            ("Bia Tiger", "Thực phẩm", 18000, "Tiger"),
            ("Xúc xích CP", "Thực phẩm", 30000, "CP"),
            
            # Điện tử
            ("iPhone 14 Pro Max", "Điện tử", 28990000, "Apple"),
            ("Samsung Galaxy S23", "Điện tử", 18990000, "Samsung"),
            ("Laptop Dell XPS", "Điện tử", 32900000, "Dell"),
            ("Tai nghe Sony WH-1000XM5", "Điện tử", 7990000, "Sony"),
            ("Apple Watch Series 8", "Điện tử", 11990000, "Apple"),
            ("Máy ảnh Canon EOS R5", "Điện tử", 85900000, "Canon"),
            ("Loa JBL Flip 6", "Điện tử", 3290000, "JBL"),
            ("Máy tính bảng iPad Air", "Điện tử", 17900000, "Apple"),
            ("Smart TV Samsung 55 inch", "Điện tử", 15900000, "Samsung"),
            ("Máy chơi game PS5", "Điện tử", 12900000, "Sony"),
            
            # Thời trang
            ("Áo thun nam cao cấp", "Thời trang", 250000, "Basic"),
            ("Váy liền nữ công sở", "Thời trang", 450000, "Fashion"),
            ("Giày thể thao Nike Air Force", "Thời trang", 2200000, "Nike"),
            ("Túi xách nữ da thật", "Thời trang", 850000, "Gucci"),
            ("Quần jeans nam", "Thời trang", 350000, "Levi's"),
            ("Áo khoác nữ", "Thời trang", 550000, "Zara"),
            ("Giày cao gót nữ", "Thời trang", 680000, "Bitis"),
            ("Đồng hồ đeo tay", "Thời trang", 1250000, "Casio"),
            ("Kính mát thời trang", "Thời trang", 280000, "Ray-Ban"),
            ("Ví da nam", "Thời trang", 320000, "Crocodile"),
            
            # Gia dụng
            ("Máy xay sinh tố Philips", "Gia dụng", 1200000, "Philips"),
            ("Nồi chiên không dầu Lock&Lock", "Gia dụng", 1850000, "Lock&Lock"),
            ("Máy hút bụi Samsung", "Gia dụng", 3200000, "Samsung"),
            ("Bình đun siêu tốc Sunhouse", "Gia dụng", 450000, "Sunhouse"),
            ("Máy giặt Toshiba", "Gia dụng", 8990000, "Toshiba"),
            ("Tủ lạnh Panasonic", "Gia dụng", 12500000, "Panasonic"),
            ("Máy lọc nước Kangaroo", "Gia dụng", 5500000, "Kangaroo"),
            ("Bếp từ đôi", "Gia dụng", 3200000, "Chefs"),
            ("Lò vi sóng", "Gia dụng", 1800000, "Sharp"),
            ("Máy sấy tóc", "Gia dụng", 350000, "Panasonic"),
            
            # Sức khỏe & Làm đẹp
            ("Son kem lì Maybelline", "Làm đẹp", 180000, "Maybelline"),
            ("Serum dưỡng ẩm La Roche-Posay", "Làm đẹp", 450000, "La Roche-Posay"),
            ("Kem chống nắng Anessa", "Làm đẹp", 520000, "Anessa"),
            ("Nước hoa Chanel No.5", "Làm đẹp", 2850000, "Chanel"),
            ("Máy đo huyết áp Omron", "Sức khỏe", 850000, "Omron"),
            ("Thực phẩm chức năng Omega-3", "Sức khỏe", 320000, "Nature Made"),
            ("Máy massage cầm tay", "Sức khỏe", 550000, "Beurer"),
            ("Nhiệt kế điện tử", "Sức khỏe", 250000, "Microlife"),
            ("Kem dưỡng da", "Làm đẹp", 380000, "Kiehl's"),
            ("Dầu gội đầu", "Làm đẹp", 120000, "Head & Shoulders"),
            
            # Sách & Văn phòng phẩm
            ("Đắc Nhân Tâm", "Sách", 85000, "First News"),
            ("Nhà Giả Kim", "Sách", 75000, "Nhã Nam"),
            ("Tư Duy Phản Biện", "Sách", 120000, "Alpha Books"),
            ("Atomic Habits", "Sách", 150000, "Penguin"),
            ("Bút bi Thiên Long", "Văn phòng phẩm", 5000, "Thiên Long"),
            ("Vở học sinh", "Văn phòng phẩm", 15000, "Campus"),
            ("Ba lô học sinh", "Văn phòng phẩm", 250000, "Simple"),
            ("Máy tính Casio", "Văn phòng phẩm", 280000, "Casio"),
            ("Bìa hồ sơ", "Văn phòng phẩm", 25000, "Deli"),
            ("Giấy in A4", "Văn phòng phẩm", 80000, "Double A")
        ]
        
        cursor.executemany(
            "INSERT INTO products (name, category, price, brand) VALUES (?, ?, ?, ?)",
            products
        )
        
        # Thêm lịch sử mua hàng mẫu - TẠO LỊCH SỬ PHONG PHÚ CHO SĐT "0899590556"
        purchases = [
            # Khách hàng 1 (0899590556) - mua nhiều sản phẩm đa dạng
            (1, 1, 3, 5), (1, 2, 2, 4), (1, 3, 1, 5), (1, 11, 1, 5), (1, 21, 2, 4),
            (1, 31, 1, 4), (1, 41, 1, 5), (1, 51, 2, 4),
            # Khách hàng 2
            (2, 1, 1, 4), (2, 4, 3, 3), (2, 5, 2, 4), (2, 22, 1, 5),
            # Khách hàng 3
            (3, 2, 2, 5), (3, 5, 1, 4), (3, 6, 1, 5), (3, 12, 1, 5),
            # Khách hàng 4
            (3, 7, 1, 4), (4, 3, 1, 5), (4, 8, 2, 4), (4, 23, 1, 4),
            # Khách hàng 5
            (5, 4, 1, 4), (5, 6, 2, 5), (5, 10, 1, 4), (5, 24, 1, 5),
            # Khách hàng 6
            (6, 7, 2, 4), (6, 13, 1, 5), (6, 32, 1, 4),
            # Khách hàng 7
            (7, 8, 1, 5), (7, 14, 1, 4), (7, 33, 1, 5),
            # Khách hàng 8
            (8, 9, 3, 4), (8, 25, 1, 5), (8, 42, 2, 4),
            # Khách hàng 9
            (9, 10, 1, 5), (9, 26, 1, 4), (9, 43, 1, 5),
            # Khách hàng 10
            (10, 15, 1, 5), (10, 34, 1, 4), (10, 44, 1, 5)
        ]
        
        cursor.executemany(
            "INSERT INTO purchase_history (customer_id, product_id, quantity, rating) VALUES (?, ?, ?, ?)",
            purchases
        )
        
        conn.commit()
        conn.close()
        print("✅ Đã thêm dữ liệu mẫu thành công!")
        print("📞 Số điện thoại mẫu để test: 0899590556 (Khách hàng Nguyễn Văn An)")
        print("📦 Đã thêm 60 sản phẩm thuộc 6 danh mục: Thực phẩm, Điện tử, Thời trang, Gia dụng, Làm đẹp, Sách")
    
    # ==================== CÁC PHƯƠNG THỨC MỚI CẦN THIẾT ====================
    
    def get_customer_by_phone(self, phone_number):
        """Tìm khách hàng bằng số điện thoại - PHƯƠNG THỨC QUAN TRỌNG"""
        conn = self.connect()
        try:
            query = "SELECT * FROM customers WHERE phone = ?"
            print(f"🔍 Đang tìm khách hàng với SĐT: {phone_number}")
            customer_df = pd.read_sql_query(query, conn, params=[phone_number])
            
            if customer_df.empty:
                print(f"❌ Không tìm thấy khách hàng với SĐT: {phone_number}")
            else:
                print(f"✅ Tìm thấy khách hàng: {customer_df.iloc[0]['name']}")
                
            return customer_df
        except Exception as e:
            print(f"❌ Lỗi khi tìm khách hàng: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    def get_customer_purchase_history(self, customer_id):
        """Lấy lịch sử mua hàng của khách hàng"""
        conn = self.connect()
        try:
            query = """
                SELECT 
                    p.product_id,
                    p.name, 
                    p.category, 
                    p.price, 
                    p.brand,
                    ph.quantity, 
                    ph.rating,
                    ph.purchase_date
                FROM purchase_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE ph.customer_id = ?
                ORDER BY ph.purchase_date DESC
            """
            history_df = pd.read_sql_query(query, conn, params=[customer_id])
            print(f"📊 Lấy được {len(history_df)} lịch sử mua hàng cho customer_id: {customer_id}")
            return history_df.to_dict('records')
        except Exception as e:
            print(f"❌ Lỗi khi lấy lịch sử mua hàng: {e}")
            return []
        finally:
            conn.close()
    
    def get_categories(self):
        """Lấy danh sách danh mục sản phẩm"""
        conn = self.connect()
        try:
            query = "SELECT DISTINCT category FROM products WHERE category IS NOT NULL ORDER BY category"
            categories_df = pd.read_sql_query(query, conn)
            categories_list = categories_df['category'].tolist()
            print(f"📋 Tìm thấy {len(categories_list)} danh mục: {categories_list}")
            return categories_list
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh mục: {e}")
            # Danh mục mặc định nếu có lỗi
            return ['Thực phẩm', 'Điện tử', 'Thời trang', 'Gia dụng', 'Làm đẹp', 'Sách']
        finally:
            conn.close()
    
    def get_products_by_category(self, category, min_price=0, max_price=100000000):
        """Lấy sản phẩm theo danh mục và khoảng giá - ĐÃ SỬA LỖI INDENTATION"""
        conn = self.connect()
        try:
            query = """
                SELECT 
                    product_id, 
                    name, 
                    category, 
                    price, 
                    brand,
                    (SELECT AVG(rating) FROM purchase_history WHERE product_id = products.product_id) as avg_rating,
                    (SELECT COUNT(*) FROM purchase_history WHERE product_id = products.product_id) as purchase_count
                FROM products 
                WHERE category = ? AND price BETWEEN ? AND ?
                ORDER BY 
                    purchase_count DESC,
                    avg_rating DESC NULLS LAST, 
                    price ASC
                LIMIT 20
            """
            products_df = pd.read_sql_query(query, conn, params=[category, min_price, max_price])
            
            # Chuyển đổi sang dictionary
            products_list = []
            for _, row in products_df.iterrows():
                product = {
                    'product_id': row['product_id'],
                    'name': row['name'],
                    'category': row['category'],
                    'price': float(row['price']),
                    'brand': row['brand'],
                    'avg_rating': float(row['avg_rating']) if row['avg_rating'] else 0,
                    'purchase_count': row['purchase_count'] or 0
                }
                products_list.append(product)
            
            print(f"🛍️ Tìm thấy {len(products_list)} sản phẩm trong danh mục '{category}'")
            return products_list
            
        except Exception as e:
            print(f"❌ Lỗi khi lấy sản phẩm theo danh mục: {e}")
            return []
        finally:
            conn.close()
    
    def get_customer_total_stats(self, customer_id):
        """Lấy thống kê tổng quan của khách hàng"""
        conn = self.connect()
        try:
            query = """
                SELECT 
                    COUNT(*) as total_purchases,
                    SUM(p.price * ph.quantity) as total_spent,
                    AVG(ph.rating) as avg_rating
                FROM purchase_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE ph.customer_id = ?
            """
            stats_df = pd.read_sql_query(query, conn, params=[customer_id])
            return {
                'total_purchases': stats_df.iloc[0]['total_purchases'] if not stats_df.empty else 0,
                'total_spent': stats_df.iloc[0]['total_spent'] if not stats_df.empty else 0,
                'avg_rating': round(stats_df.iloc[0]['avg_rating'], 1) if not stats_df.empty and stats_df.iloc[0]['avg_rating'] else 0
            }
        except Exception as e:
            print(f"❌ Lỗi khi lấy thống kê khách hàng: {e}")
            return {'total_purchases': 0, 'total_spent': 0, 'avg_rating': 0}
        finally:
            conn.close()
    
    def get_system_stats(self):
        """Thống kê hệ thống"""
        conn = self.connect()
        try:
            stats = {
                'total_customers': pd.read_sql("SELECT COUNT(*) as count FROM customers", conn).iloc[0]['count'],
                'total_products': pd.read_sql("SELECT COUNT(*) as count FROM products", conn).iloc[0]['count'],
                'total_purchases': pd.read_sql("SELECT COUNT(*) as count FROM purchase_history", conn).iloc[0]['count'],
                'total_revenue': pd.read_sql("""
                    SELECT SUM(p.price * ph.quantity) as revenue 
                    FROM purchase_history ph 
                    JOIN products p ON ph.product_id = p.product_id
                """, conn).iloc[0]['revenue'] or 0,
                'avg_rating': pd.read_sql("SELECT AVG(rating) as avg_rating FROM purchase_history WHERE rating > 0", conn).iloc[0]['avg_rating'] or 0
            }
            return stats
        except Exception as e:
            print(f"❌ Lỗi khi lấy thống kê hệ thống: {e}")
            return {}
        finally:
            conn.close()

    # ==================== PHƯƠNG THỨC KIỂM TRA ====================
    
    def test_database(self):
        """Kiểm tra database có hoạt động không"""
        try:
            conn = self.connect()
            
            # Kiểm tra tables
            tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
            tables_df = pd.read_sql_query(tables_query, conn)
            print("📊 Tables trong database:", tables_df['name'].tolist())
            
            # Kiểm tra số lượng bản ghi
            for table in ['customers', 'products', 'purchase_history']:
                if table in tables_df['name'].values:
                    count_query = f"SELECT COUNT(*) as count FROM {table}"
                    count_df = pd.read_sql_query(count_query, conn)
                    print(f"   {table}: {count_df.iloc[0]['count']} bản ghi")
            
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Lỗi kiểm tra database: {e}")
            return False

if __name__ == "__main__":
    db = DatabaseManager()
    
    print("🚀 Khởi tạo database...")
    db.create_tables()
    db.insert_sample_data()
    
    print("\n🧪 Kiểm tra database...")
    db.test_database()
    
    print("\n🔍 Test tìm kiếm khách hàng...")
    test_phone = "0899590556"
    customer = db.get_customer_by_phone(test_phone)
    if not customer.empty:
        customer_id = customer.iloc[0]['customer_id']
        print(f"✅ Tìm thấy: {customer.iloc[0]['name']} (ID: {customer_id})")
        
        # Test lấy lịch sử mua hàng
        history = db.get_customer_purchase_history(customer_id)
        print(f"📦 Lịch sử mua hàng: {len(history)} sản phẩm")
        
        # Test lấy danh mục
        categories = db.get_categories()
        print(f"📋 Danh mục: {categories}")
        
        # Test lấy sản phẩm theo danh mục
        if categories:
            test_category = categories[0]
            products = db.get_products_by_category(test_category)
            print(f"🛍️ Sản phẩm trong '{test_category}': {len(products)} sản phẩm")
        
        # Test lấy thống kê
        stats = db.get_customer_total_stats(customer_id)
        print(f"📊 Thống kê: {stats}")
    else:
        print("❌ Không tìm thấy khách hàng test")
    
    print("\n✅ Database ready!")