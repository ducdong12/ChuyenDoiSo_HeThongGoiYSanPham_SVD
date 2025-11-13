import pandas as pd
import numpy as np
import os
import sys

# Thêm path để import từ cùng level
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)

try:
    from utils.database import DatabaseManager
except ImportError:
    # Fallback import
    import importlib.util
    spec = importlib.util.spec_from_file_location("database", os.path.join(current_dir, "database.py"))
    database_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database_module)
    DatabaseManager = database_module.DatabaseManager

class DataLoader:
    def __init__(self):
        self.db = DatabaseManager()
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(current_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_local_dataset(self):
        """Load dataset từ file local"""
        csv_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]
        if not csv_files:
            print("❌ Không tìm thấy file CSV nào")
            return False
        
        # Ưu tiên file ecommerce
        preferred_files = [f for f in csv_files if any(keyword in f.lower() for keyword in 
                        ['ecommerce', 'transaction', 'customer'])]
        target_file = preferred_files[0] if preferred_files else csv_files[0]
        
        return self.process_local_file(target_file)
    
    def process_local_file(self, csv_file):
        """Xử lý file CSV"""
        try:
            file_path = os.path.join(self.data_dir, csv_file)
            df = pd.read_csv(file_path)
            
            # Chuẩn hóa tên cột
            df = self.standardize_columns(df)
            
            # Xử lý đặc biệt cho ecommerce
            if any(keyword in csv_file.lower() for keyword in ['ecommerce', 'e-commerce']):
                return self.process_ecommerce_dataset(df)
            
            return self.load_to_database(df)
            
        except Exception as e:
            print(f"❌ Lỗi xử lý file: {e}")
            return False

    def process_ecommerce_dataset(self, df):
        """Xử lý dataset ecommerce"""
        required_columns = ['customer_id', 'product_id', 'rating']
        if not all(col in df.columns for col in required_columns):
            return self.load_to_database(df)
        
        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Xóa dữ liệu cũ
        cursor.execute("DELETE FROM purchase_history")
        cursor.execute("DELETE FROM products") 
        cursor.execute("DELETE FROM customers")
        
        # Thêm khách hàng
        unique_customers = df['customer_id'].dropna().unique()
        for customer_id in unique_customers:
            cursor.execute("INSERT INTO customers (customer_id, name) VALUES (?, ?)",
                          (int(customer_id), f'Customer_{customer_id}'))
        
        # Thêm sản phẩm
        unique_products = df['product_id'].dropna().unique()
        categories = ['Điện tử', 'Thời trang', 'Gia dụng', 'Sách', 'Thể thao']
        brands = ['Apple', 'Samsung', 'Sony', 'Nike', 'Adidas']
        
        for i, product_id in enumerate(unique_products):
            category = categories[i % len(categories)]
            brand = brands[i % len(brands)]
            cursor.execute(
                "INSERT INTO products (product_id, name, category, price, brand) VALUES (?, ?, ?, ?, ?)",
                (int(product_id), f'{brand} {category} {product_id}', category, 
                 np.random.randint(50000, 5000000), brand)
            )
        
        # Thêm lịch sử mua hàng
        for _, row in df.iterrows():
            cursor.execute(
                "INSERT INTO purchase_history (customer_id, product_id, quantity, rating) VALUES (?, ?, ?, ?)",
                (int(row['customer_id']), int(row['product_id']), 1, int(row['rating']))
            )
        
        conn.commit()
        conn.close()
        return True
    
    def standardize_columns(self, df):
        """Chuẩn hóa tên cột"""
        column_mapping = {
            'customer_id': 'customer_id', 'user_id': 'customer_id',
            'product_id': 'product_id', 'item_id': 'product_id',
            'product_name': 'product_name', 'name': 'product_name',
            'category': 'category', 'price': 'price', 'rating': 'rating'
        }
        return df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    def load_to_database(self, df):
        """Load dữ liệu vào database"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Xóa dữ liệu cũ
            cursor.execute("DELETE FROM purchase_history")
            cursor.execute("DELETE FROM products")
            cursor.execute("DELETE FROM customers")
            
            # Xử lý khách hàng
            if 'customer_id' not in df.columns:
                df['customer_id'] = range(1, len(df) + 1)
            
            unique_customers = df['customer_id'].dropna().unique()
            for customer_id in unique_customers:
                cursor.execute("INSERT INTO customers (customer_id, name) VALUES (?, ?)",
                              (int(customer_id), f'Customer_{customer_id}'))
            
            # Xử lý sản phẩm
            if 'product_id' not in df.columns and 'product_name' in df.columns:
                unique_products = df['product_name'].dropna().unique()
                product_mapping = {name: i+1 for i, name in enumerate(unique_products)}
                df['product_id'] = df['product_name'].map(product_mapping)
            
            unique_products = df['product_id'].dropna().unique()
            categories = ['Điện tử', 'Thời trang', 'Gia dụng', 'Sách', 'Thể thao']
            brands = ['Apple', 'Samsung', 'Sony', 'Nike', 'Adidas']
            
            for product_id in unique_products:
                product_data = df[df['product_id'] == product_id].iloc[0]
                name = product_data.get('product_name', f'Product_{product_id}')
                category = product_data.get('category', categories[product_id % len(categories)])
                price = product_data.get('price', np.random.randint(10000, 500000))
                
                cursor.execute(
                    "INSERT INTO products (product_id, name, category, price, brand) VALUES (?, ?, ?, ?, ?)",
                    (int(product_id), str(name), str(category), float(price), brands[product_id % len(brands)])
                )
            
            # Thêm lịch sử mua hàng
            for _, row in df.iterrows():
                cursor.execute(
                    "INSERT INTO purchase_history (customer_id, product_id, quantity, rating) VALUES (?, ?, ?, ?)",
                    (int(row['customer_id']), int(row['product_id']), 
                     int(row.get('quantity', 1)), int(row.get('rating', np.random.randint(3, 6))))
                )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Lỗi load database: {e}")
            return False

if __name__ == "__main__":
    loader = DataLoader()
    success = loader.load_local_dataset()
    print("✅ Thành công!" if success else "❌ Thất bại!")