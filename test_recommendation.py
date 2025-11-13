# test_recommendation.py
import sys
import os
import requests
import json

# Thêm src vào path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

def test_all_apis():
    """Test tất cả APIs"""
    base_url = "http://localhost:5000"
    
    print("🧪 TEST TOÀN BỘ HỆ THỐNG API")
    print("=" * 60)
    
    # Test 1: Lấy danh mục
    print("1. 📋 Testing /api/categories...")
    try:
        response = requests.get(f"{base_url}/api/categories")
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Categories: {data.get('categories', [])}")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    # Test 2: Tìm khách hàng
    print("\n2. 👤 Testing /api/customer/search...")
    try:
        response = requests.post(
            f"{base_url}/api/customer/search",
            json={"phone": "0899590556"}
        )
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Found: {data.get('found')}")
        if data.get('found'):
            customer = data['customer']
            print(f"   Customer: {customer['name']} (ID: {customer['customer_id']})")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    # Test 3: Gợi ý manual
    print("\n3. 🎯 Testing /api/recommend/manual...")
    try:
        response = requests.post(
            f"{base_url}/api/recommend/manual",
            json={"categories": ["Điện tử", "Thời trang"], "n_recommendations": 3}
        )
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Count: {data.get('count')}")
        if data.get('success'):
            print(f"   Recommendations: {len(data.get('recommendations', []))} sản phẩm")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")
    
    # Test 4: Gợi ý smart
    print("\n4. 🧠 Testing /api/recommend/smart...")
    try:
        response = requests.post(
            f"{base_url}/api/recommend/smart",
            json={"customer_id": 1, "n_recommendations": 3}
        )
        data = response.json()
        print(f"   Status: {response.status_code}")
        print(f"   Success: {data.get('success')}")
        print(f"   Count: {data.get('count')}")
        if data.get('success'):
            print(f"   Recommendations: {len(data.get('recommendations', []))} sản phẩm")
    except Exception as e:
        print(f"   ❌ Lỗi: {e}")

if __name__ == "__main__":
    test_all_apis()