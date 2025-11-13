import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from scipy.sparse.linalg import svds
import sys
import os
from datetime import datetime, timedelta
import random
import math

# Sửa import path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)

try:
    from utils.database import DatabaseManager
except ImportError as e:
    print(f"Lỗi import database: {e}")
    # Fallback import
    import importlib.util
    spec = importlib.util.spec_from_file_location("database", os.path.join(src_dir, "utils", "database.py"))
    database_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database_module)
    DatabaseManager = database_module.DatabaseManager


class AdvancedRecommender:
    def __init__(self):
        self.db = DatabaseManager()
        self.algorithm = "hybrid"
        self.user_profiles = {}
        self.product_features = {}
        self.category_diversity_boost = 0.3  # Tăng cường đa dạng danh mục

        # ===== Trạng thái phiên để reset khi nhập khách hàng mới =====
        self._current_customer_id = None
        self._session_recommended_ids = set()

    # ---------------------- Helpers chung ----------------------

    def set_algorithm(self, algorithm):
        """Thiết lập thuật toán với validation"""
        valid_algorithms = ["collaborative", "content", "hybrid", "popular", "svd", "weighted_hybrid", "diverse_hybrid"]
        if algorithm in valid_algorithms:
            self.algorithm = algorithm
            print(f"✅ Đã thiết lập thuật toán: {algorithm}")
        else:
            print(f"⚠️ Thuật toán '{algorithm}' không hợp lệ. Sử dụng 'hybrid' mặc định.")
            self.algorithm = "hybrid"

    def _reset_state_for_new_customer(self, new_customer_id: int):
        """
        Reset toàn bộ trạng thái/caching nội bộ khi chuyển sang khách hàng mới.
        Gọi tự động trong recommend_products(...) nếu customer_id thay đổi.
        """
        self._current_customer_id = new_customer_id
        self.user_profiles = {}
        self.product_features = {}
        self._session_recommended_ids = set()
        print("🔄 Đã reset trạng thái gợi ý cho khách hàng mới.")

    def reset_for_new_customer(self, new_customer_id: int):
        """
        Public wrapper để API gọi reset khi chuyển khách hàng.
        """
        self._reset_state_for_new_customer(new_customer_id)

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Kiểm tra cột có tồn tại trong bảng SQLite không."""
        conn = self.db.connect()
        try:
            df = pd.read_sql(f"PRAGMA table_info({table_name})", conn)
            return column_name in set(df["name"].tolist())
        except Exception as e:
            print(f"❌ Lỗi kiểm tra cột {column_name} trong {table_name}: {e}")
            return False
        finally:
            conn.close()

    def _get_user_purchased_ids(self, customer_id: int):
        """Lấy set product_id mà user đã mua để loại trừ khỏi gợi ý."""
        conn = self.db.connect()
        try:
            df = pd.read_sql(
                "SELECT DISTINCT product_id FROM purchase_history WHERE customer_id = ?",
                conn, params=[customer_id]
            )
            return set(df["product_id"].tolist())
        except Exception as e:
            print(f"❌ Lỗi lấy danh sách sản phẩm đã mua: {e}")
            return set()
        finally:
            conn.close()

    def get_category_diversity_score(self, product_category, recommended_categories):
        """Tính điểm đa dạng danh mục - khuyến khích danh mục mới"""
        if not recommended_categories:
            return 1.0
        category_count = recommended_categories.count(product_category)
        if category_count == 0:
            return 1.0 + self.category_diversity_boost
        else:
            return 1.0 / (category_count + 1)

    def get_all_categories(self):
        """Lấy tất cả danh mục sản phẩm có trong hệ thống"""
        conn = self.db.connect()
        try:
            query = "SELECT DISTINCT category FROM products WHERE category IS NOT NULL"
            categories_df = pd.read_sql(query, conn)
            return categories_df["category"].tolist()
        except Exception as e:
            print(f"❌ Lỗi khi lấy danh mục: {e}")
            return ["Thực phẩm", "Điện tử", "Gia dụng", "Thời trang", "Sức khỏe"]
        finally:
            conn.close()

    # ---------------------- User profile & matrix ----------------------

    def build_enhanced_user_profile(self, customer_id):
        """Xây dựng hồ sơ người dùng mở rộng với đa dạng danh mục"""
        conn = self.db.connect()
        try:
            query = """
                SELECT 
                    p.category,
                    p.brand,
                    AVG(ph.rating) as avg_rating,
                    COUNT(ph.purchase_id) as purchase_count,
                    MAX(ph.purchase_date) as last_purchase,
                    p.price
                FROM purchase_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE ph.customer_id = ?
                GROUP BY p.category, p.brand
                HAVING COUNT(ph.purchase_id) > 0
            """
            profile_df = pd.read_sql(query, conn, params=[customer_id])

            if profile_df.empty:
                return None

            profile_df["preference_score"] = (
                profile_df["avg_rating"] * 0.5
                + profile_df["purchase_count"] * 0.3
                + (profile_df["price"] / max(profile_df["price"].max(), 1)) * 0.2
            )

            category_scores = profile_df.groupby("category")["preference_score"].mean()
            total_categories = len(category_scores)

            user_profile = {
                "preferred_categories": category_scores.to_dict(),
                "preferred_brands": profile_df.set_index("brand")["preference_score"].to_dict(),
                "total_purchases": int(profile_df["purchase_count"].sum()),
                "avg_rating": float(profile_df["avg_rating"].mean()),
                "category_variety": total_categories,
                "preferred_price_range": {
                    "min": float(profile_df["price"].min()),
                    "max": float(profile_df["price"].max()),
                    "avg": float(profile_df["price"].mean()),
                },
            }

            self.user_profiles[customer_id] = user_profile
            return user_profile

        except Exception as e:
            print(f"❌ Lỗi build user profile: {e}")
            return None
        finally:
            conn.close()

    def get_enhanced_user_item_matrix(self):
        """
        Lấy ma trận người dùng - sản phẩm với thông tin mở rộng.
        Sửa về cú pháp SQLite: dùng julianday('now') thay TIMESTAMPDIFF/NOW().
        """
        conn = self.db.connect()
        try:
            df = pd.read_sql(
                """
                SELECT 
                    ph.customer_id, 
                    ph.product_id, 
                    ph.rating,
                    ph.purchase_date,
                    p.category,
                    p.brand,
                    p.price,
                    CAST((julianday('now') - julianday(ph.purchase_date)) AS INTEGER) AS days_since_purchase
                FROM purchase_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE ph.rating > 0
                ORDER BY ph.purchase_date DESC
                """,
                conn,
            )

            if df.empty:
                return None, None, None

            # Trọng số thời gian: mua gần → trọng số cao
            df["time_weight"] = np.exp(-df["days_since_purchase"] / 30.0)
            df["weighted_rating"] = df["rating"] * df["time_weight"]

            user_item_matrix = df.pivot_table(
                index="customer_id",
                columns="product_id",
                values="weighted_rating",
                fill_value=0,
                aggfunc="mean",
            )
            return user_item_matrix, user_item_matrix.index, user_item_matrix.columns

        except Exception as e:
            print(f"❌ Lỗi get user item matrix: {e}")
            return None, None, None
        finally:
            conn.close()

    # ---------------------- CF / SVD ----------------------

    def collaborative_filtering(self, customer_id, n_recommendations=10):
        """Collaborative Filtering với đa dạng danh mục"""
        user_item_matrix, user_ids, product_ids = self.get_enhanced_user_item_matrix()

        if user_item_matrix is None or customer_id not in user_ids:
            return self.get_diverse_popular_products(n_recommendations)

        try:
            user_similarity = cosine_similarity(user_item_matrix)
            user_similarity_df = pd.DataFrame(user_similarity, index=user_ids, columns=user_ids)

            similar_users = user_similarity_df[customer_id].sort_values(ascending=False)[1:11]
            similar_users = similar_users[similar_users > 0.1]

            if len(similar_users) == 0:
                return self.get_diverse_popular_products(n_recommendations)

            product_scores = {}
            user_purchased = user_item_matrix.columns[user_item_matrix.loc[customer_id] > 0].tolist()

            for similar_user_id, similarity_score in similar_users.items():
                user_ratings = user_item_matrix.loc[similar_user_id]
                for product_id in user_ratings.index:
                    if user_ratings[product_id] > 0 and product_id not in user_purchased:
                        product_scores[product_id] = product_scores.get(product_id, 0.0) + (
                            user_ratings[product_id] * similarity_score
                        )

            top_products = self.apply_category_diversity(product_scores, n_recommendations)
            return self.get_product_details(top_products, "Khách hàng tương tự mua")

        except Exception as e:
            print(f"❌ Lỗi collaborative filtering: {e}")
            return self.get_diverse_popular_products(n_recommendations)

    def svd_recommendation(self, customer_id, n_recommendations=10):
        """SVD recommendation với đa dạng hóa"""
        user_item_matrix, user_ids, product_ids = self.get_enhanced_user_item_matrix()

        if user_item_matrix is None or customer_id not in user_ids:
            return self.get_diverse_popular_products(n_recommendations)

        try:
            user_means = user_item_matrix.mean(axis=1)
            normalized_matrix = user_item_matrix.sub(user_means, axis=0).fillna(0)

            R = normalized_matrix.values.astype(np.float64)
            k = min(20, max(min(R.shape) - 1, 2))
            if k < 2:
                return self.get_diverse_popular_products(n_recommendations)

            U, sigma, Vt = svds(R, k=k, which="LM")
            sigma = np.diag(sigma)

            predicted_ratings = np.dot(np.dot(U, sigma), Vt) + user_means.values.reshape(-1, 1)
            predicted_df = pd.DataFrame(predicted_ratings, index=user_ids, columns=product_ids)

            user_idx = list(user_ids).index(customer_id)
            user_predictions = predicted_df.iloc[user_idx]

            user_purchased = user_item_matrix.columns[user_item_matrix.loc[customer_id] > 0].tolist()
            candidate_products = [(pid, score) for pid, score in user_predictions.items() if pid not in user_purchased and score > 0.1]

            top_products = self.apply_category_diversity(dict(candidate_products), n_recommendations)
            return self.get_product_details(top_products, "Dự đoán theo hành vi")

        except Exception as e:
            print(f"❌ Lỗi SVD recommendation: {e}")
            return self.get_diverse_popular_products(n_recommendations)

    def apply_category_diversity(self, product_scores, n_recommendations):
        """Áp dụng đa dạng hóa danh mục cho danh sách sản phẩm"""
        if not product_scores:
            return []

        conn = self.db.connect()
        try:
            product_ids = list(product_scores.keys())
            if not product_ids:
                return []
            placeholders = ",".join(["?"] * len(product_ids))
            query = f"""
                SELECT product_id, category 
                FROM products 
                WHERE product_id IN ({placeholders})
            """
            categories_df = pd.read_sql(query, conn, params=product_ids)

            category_groups = {}
            for _, row in categories_df.iterrows():
                category = row["category"]
                pid = row["product_id"]
                category_groups.setdefault(category, []).append((pid, product_scores[pid]))

            for category in category_groups:
                category_groups[category].sort(key=lambda x: x[1], reverse=True)

            final_products = []
            selected_categories = set()

            while len(final_products) < n_recommendations and category_groups:
                available_categories = [c for c in category_groups if c not in selected_categories] or list(category_groups.keys())
                for category in available_categories:
                    if category_groups[category]:
                        pid, score = category_groups[category].pop(0)
                        final_products.append((pid, score))
                        selected_categories.add(category)
                        if len(final_products) >= n_recommendations:
                            break
                category_groups = {c: v for c, v in category_groups.items() if v}

            return final_products[:n_recommendations]

        except Exception as e:
            print(f"❌ Lỗi apply category diversity: {e}")
            return sorted(product_scores.items(), key=lambda x: x[1], reverse=True)[:n_recommendations]
        finally:
            conn.close()

    # ---------------------- Content-based ----------------------

    def content_based_filtering(self, customer_id, n_recommendations=10):
        """
        Content-Based Filtering:
        - Tự động bỏ cột 'description' nếu schema không có (tránh lỗi 'no such column: description').
        - Loại trừ sản phẩm user đã mua.
        """
        user_profile = self.build_enhanced_user_profile(customer_id)
        if not user_profile:
            return self.get_diverse_popular_products(n_recommendations)

        conn = self.db.connect()
        try:
            base_cols = ["product_id", "name", "category", "brand", "price"]
            if self._column_exists("products", "description"):
                base_cols.append("description")
            select_cols = ", ".join(base_cols)

            products_df = pd.read_sql(
                f"""
                SELECT {select_cols}
                FROM products
                WHERE product_id NOT IN (
                    SELECT product_id FROM purchase_history WHERE customer_id = ?
                )
                """,
                conn, params=[customer_id]
            )

            if products_df.empty:
                return self.get_diverse_popular_products(n_recommendations)

            # Bảo vệ cột text
            for c in ["name", "category", "brand"]:
                if c not in products_df.columns:
                    products_df[c] = ""
            if "description" not in products_df.columns:
                products_df["description"] = ""

            # Ghép trường văn bản cho vector hoá (nếu bạn có dùng)
            products_df["__text__"] = (
                products_df["name"].astype(str) + " "
                + products_df["category"].astype(str) + " "
                + products_df["brand"].astype(str) + " "
                + products_df["description"].astype(str)
            ).str.strip()

            # Chấm điểm “mềm” theo hồ sơ + random nhỏ để đa dạng
            product_scores = []
            for _, product in products_df.iterrows():
                score = 0.0
                reason_parts = []

                # Category
                cat_score = user_profile["preferred_categories"].get(product["category"], 0.0)
                if cat_score > 0:
                    score += cat_score * 0.3
                    reason_parts.append(f"phù hợp {product['category']}")
                else:
                    score += 0.2
                    reason_parts.append(f"khám phá {product['category']}")

                # Brand
                brand_score = user_profile["preferred_brands"].get(product["brand"], 0.0)
                if brand_score > 0:
                    score += brand_score * 0.3
                    reason_parts.append(f"thương hiệu {product['brand']}")

                # Price
                price_score = self.calculate_price_affinity(customer_id, float(product["price"]))
                score += price_score * 0.2

                # Đa dạng nhẹ
                score += random.uniform(0, 0.2)

                if score > 0:
                    product_scores.append({
                        "product_id": product["product_id"],
                        "score": float(score),
                        "reason": f"Sản phẩm {' & '.join(reason_parts)}",
                        "category": product["category"],
                    })

            diversified = self.diversify_recommendations(product_scores, n_recommendations)
            # Ghi nhận ID đã gợi ý trong phiên (tuỳ bạn sử dụng sau này)
            for p in diversified:
                self._session_recommended_ids.add(p["product_id"])

            return self.get_products_by_ids(
                [p["product_id"] for p in diversified],
                [p["reason"] for p in diversified],
                [p["score"] for p in diversified],
            )

        except Exception as e:
            print(f"❌ Lỗi content-based filtering: {e}")
            return self.get_diverse_popular_products(n_recommendations)
        finally:
            conn.close()

    def diversify_recommendations(self, product_scores, n_recommendations):
        """Đa dạng hóa danh sách gợi ý theo category"""
        if not product_scores:
            return []

        category_groups = {}
        for product in product_scores:
            category_groups.setdefault(product["category"], []).append(product)

        for category in category_groups:
            category_groups[category].sort(key=lambda x: x["score"], reverse=True)

        final_products = []
        selected_categories = set()

        while len(final_products) < n_recommendations and category_groups:
            available_categories = [c for c in category_groups if c not in selected_categories] or list(category_groups.keys())
            for category in available_categories:
                if category_groups[category]:
                    product = category_groups[category].pop(0)
                    final_products.append(product)
                    selected_categories.add(category)
                    if len(final_products) >= n_recommendations:
                        break
            category_groups = {c: v for c, v in category_groups.items() if v}

        return final_products[:n_recommendations]

    # ---------------------- Popular & Random ----------------------

    def get_diverse_popular_products(self, n_recommendations=10):
        """Lấy sản phẩm phổ biến với đa dạng danh mục"""
        conn = self.db.connect()
        try:
            query = """
                SELECT 
                    p.product_id, 
                    p.name, 
                    p.category, 
                    p.price, 
                    p.brand,
                    COUNT(ph.purchase_id) as purchase_count,
                    COALESCE(AVG(ph.rating), 0) as avg_rating,
                    COUNT(DISTINCT ph.customer_id) as unique_customers
                FROM products p
                LEFT JOIN purchase_history ph ON p.product_id = ph.product_id
                GROUP BY p.product_id, p.category
                HAVING COUNT(ph.purchase_id) > 0
                ORDER BY p.category, 
                    (COUNT(ph.purchase_id) * 0.6 + 
                     AVG(ph.rating) * 0.3 + 
                     COUNT(DISTINCT ph.customer_id) * 0.1) DESC
            """
            df = pd.read_sql(query, conn)

            if df.empty:
                print("⚠️ Không có sản phẩm phổ biến, trả về sản phẩm ngẫu nhiên")
                return self.get_random_products(n_recommendations)

            # Lấy 2 top mỗi category, rồi cắt theo n
            final_products = []
            for category, group in df.groupby("category"):
                final_products.extend(group.head(2).to_dict("records"))
                if len(final_products) >= n_recommendations * 2:
                    break

            results = []
            for product in final_products[:n_recommendations]:
                popularity_score = (
                    product["purchase_count"] * 0.6
                    + product["avg_rating"] * 0.3
                    + product["unique_customers"] * 0.1
                ) / 10.0

                results.append({
                    "product_id": product["product_id"],
                    "name": product["name"],
                    "category": product["category"],
                    "price": float(product["price"]),
                    "brand": product["brand"],
                    "avg_rating": float(product["avg_rating"]),
                    "score": float(popularity_score),
                    "reason": f"Sản phẩm phổ biến (⭐{product['avg_rating']:.1f}, 👥{product['unique_customers']})",
                })

            print(f"✅ Trả về {len(results)} sản phẩm phổ biến đa dạng")
            return results

        except Exception as e:
            print(f"❌ Lỗi get diverse popular products: {e}")
            return self.get_random_products(n_recommendations)
        finally:
            conn.close()

    def get_random_products(self, n_recommendations=10):
        """Lấy sản phẩm ngẫu nhiên như fallback"""
        conn = self.db.connect()
        try:
            df = pd.read_sql_query(
                """
                SELECT product_id, name, category, price, brand
                FROM products 
                ORDER BY RANDOM() 
                LIMIT ?
                """,
                conn, params=[n_recommendations]
            )

            results = []
            for _, row in df.iterrows():
                results.append({
                    "product_id": row["product_id"],
                    "name": row["name"],
                    "category": row["category"],
                    "price": float(row["price"]),
                    "brand": row["brand"],
                    "avg_rating": 4.0,  # giả định
                    "score": 0.5,
                    "reason": "Sản phẩm đề xuất ngẫu nhiên",
                })
            return results

        except Exception as e:
            print(f"❌ Lỗi get random products: {e}")
            return []
        finally:
            conn.close()

    # ---------------------- Price affinity ----------------------

    def calculate_price_affinity(self, customer_id, product_price):
        """Tính độ phù hợp về giá dựa trên lịch sử mua hàng (SQLite-safe)"""
        conn = self.db.connect()
        try:
            price_query = """
                SELECT p.price
                FROM purchase_history ph
                JOIN products p ON ph.product_id = p.product_id
                WHERE ph.customer_id = ? AND ph.rating >= 4
            """
            prices_df = pd.read_sql_query(price_query, conn, params=[customer_id])

            if prices_df.empty:
                return 0.5

            prices = prices_df["price"].astype(float).values
            avg_price = float(np.mean(prices))
            std_price = float(np.std(prices, ddof=0))  # population std
            if std_price == 0:
                std_price = max(avg_price * 0.5, 1.0)

            price_diff = abs(product_price - avg_price)
            if price_diff <= std_price:
                return 1.0 - (price_diff / std_price) * 0.5
            else:
                return max(0.0, 0.5 - (price_diff - std_price) / std_price)

        except Exception as e:
            print(f"❌ Lỗi calculate price affinity: {e}")
            return 0.5
        finally:
            conn.close()

    # ---------------------- Hybrid (đã gộp theo product_id) ----------------------

    def hybrid_recommendation(self, customer_id, n_recommendations=10):
        """
        Hybrid recommendation với:
        - Gộp theo product_id từ nhiều nguồn (popular/content/collab/svd)
        - Cộng trọng số, chuẩn hóa [0,1]
        - Loại trừ sản phẩm đã mua
        - Đa dạng hóa & khử trùng theo product_id
        """
        user_profile = self.build_enhanced_user_profile(customer_id)

        if not user_profile or user_profile.get("total_purchases", 0) < 5:
            weights = {"popular": 0.3, "content": 0.4, "collaborative": 0.2, "svd": 0.1}
        elif user_profile.get("total_purchases", 0) > 20 and user_profile.get("category_variety", 0) < 3:
            weights = {"popular": 0.2, "content": 0.3, "collaborative": 0.2, "svd": 0.3}
        else:
            weights = {"popular": 0.2, "content": 0.3, "collaborative": 0.25, "svd": 0.25}

        purchased_ids = self._get_user_purchased_ids(customer_id)

        # Lấy dư để diversify
        k = max(n_recommendations * 2, 20)
        sources = {
            "popular": self.get_diverse_popular_products(k),
            "content": self.content_based_filtering(customer_id, k),
            "collaborative": self.collaborative_filtering(customer_id, k),
            "svd": self.svd_recommendation(customer_id, k),
        }

        # Gộp theo product_id
        agg = {}  # pid -> {product_id, category, brand, price, final_score, reasons}
        for src_name, recs in sources.items():
            w = float(weights.get(src_name, 0.0))
            if not recs:
                continue
            for r in recs:
                pid = r.get("product_id")
                if not pid or pid in purchased_ids:
                    continue
                base_score = float(r.get("score", 1.0))
                contrib = base_score * w
                if pid not in agg:
                    agg[pid] = {
                        "product_id": pid,
                        "category": r.get("category"),
                        "brand": r.get("brand"),
                        "price": r.get("price"),
                        "final_score": 0.0,
                        "reasons": [],
                    }
                agg[pid]["final_score"] += contrib
                reason_text = r.get("reason") or src_name
                agg[pid]["reasons"].append(f"{src_name}: {reason_text} (×{w:.2f})")

        if not agg:
            return self.get_diverse_popular_products(n_recommendations)

        # Chuẩn hóa [0,1]
        scores = [v["final_score"] for v in agg.values()]
        s_min, s_max = min(scores), max(scores)
        for v in agg.values():
            if s_max > s_min:
                v["final_score"] = (v["final_score"] - s_min) / (s_max - s_min)
            else:
                v["final_score"] = 0.5

        merged_list = sorted(agg.values(), key=lambda x: x["final_score"], reverse=True)

        product_scores = []
        for v in merged_list:
            merged_reason = " | ".join(dict.fromkeys(v["reasons"]))  # unique theo thứ tự
            product_scores.append({
                "product_id": v["product_id"],
                "category": v.get("category", "Khác"),
                "score": float(v["final_score"]),
                "reason": merged_reason,
                "final_score": float(v["final_score"]),
            })

        diversified = self.final_diversification(product_scores, n_recommendations)

        ids = [x["product_id"] for x in diversified]
        reasons = [x.get("reason") for x in diversified]
        scores = [float(x.get("final_score", x.get("score", 0))) for x in diversified]

        # Ghi nhận ID đã gợi ý trong phiên (nếu bạn cần dùng ở UI)
        for pid in ids:
            self._session_recommended_ids.add(pid)

        return self.get_products_by_ids(ids, reasons, scores)

    def final_diversification(self, all_recommendations, n_recommendations):
        """Đa dạng hóa cuối cùng; khử trùng theo product_id thay vì so dict object."""
        if not all_recommendations:
            return []

        # Nhóm theo category
        category_groups = {}
        for rec in all_recommendations:
            cat = rec.get("category", "Khác") or "Khác"
            category_groups.setdefault(cat, []).append(rec)

        # Sắp xếp từng nhóm
        def _score(x):
            return x.get("final_score", x.get("score", 0.0))

        for cat in category_groups:
            category_groups[cat].sort(key=_score, reverse=True)

        final_recs = []
        seen_ids = set()

        # Mỗi category lấy 1 top
        for cat in list(category_groups.keys()):
            if category_groups[cat]:
                top = category_groups[cat].pop(0)
                pid = top.get("product_id")
                if pid and pid not in seen_ids:
                    final_recs.append(top)
                    seen_ids.add(pid)
                    if len(final_recs) >= n_recommendations:
                        for rec in final_recs:
                            fs = rec.get("final_score", rec.get("score", 0))
                            rec["reason"] = f"{rec.get('reason','')} | Điểm tổng hợp: {fs:.2f}".strip()
                        return final_recs[:n_recommendations]

        # Lấp đầy từ phần còn lại
        rest = []
        for lst in category_groups.values():
            rest.extend(lst)
        rest.sort(key=_score, reverse=True)

        for item in rest:
            if len(final_recs) >= n_recommendations:
                break
            pid = item.get("product_id")
            if pid and pid not in seen_ids:
                final_recs.append(item)
                seen_ids.add(pid)

        for rec in final_recs:
            fs = rec.get("final_score", rec.get("score", 0))
            rec["reason"] = f"{rec.get('reason','')} | Đa dạng hóa danh mục | Điểm tổng hợp: {fs:.2f}".strip()

        return final_recs[:n_recommendations]

    # ---------------------- Misc utils ----------------------

    def get_popular_products(self, n_recommendations=10):
        """Phương thức cũ để backup"""
        conn = self.db.connect()
        query = """
            SELECT 
                p.product_id, 
                p.name, 
                p.category, 
                p.price, 
                p.brand,
                COUNT(ph.purchase_id) as purchase_count,
                AVG(ph.rating) as avg_rating,
                COUNT(DISTINCT ph.customer_id) as unique_customers
            FROM products p
            LEFT JOIN purchase_history ph ON p.product_id = ph.product_id
            GROUP BY p.product_id
            HAVING COUNT(ph.purchase_id) > 0
            ORDER BY 
                (COUNT(ph.purchase_id) * 0.6 + 
                 AVG(ph.rating) * 0.3 + 
                 COUNT(DISTINCT ph.customer_id) * 0.1) DESC
            LIMIT ?
        """
        df = pd.read_sql(query, conn, params=[n_recommendations * 2])
        conn.close()

        results = []
        for _, row in df.iterrows():
            popularity_score = (
                row["purchase_count"] * 0.6 + row["avg_rating"] * 0.3 + row["unique_customers"] * 0.1
            ) / 10.0
            results.append({
                "product_id": row["product_id"],
                "name": row["name"],
                "category": row["category"],
                "price": float(row["price"]),
                "brand": row["brand"],
                "score": float(popularity_score),
                "reason": f"Sản phẩm phổ biến (⭐{row['avg_rating']:.1f}, 👥{row['unique_customers']})",
            })
        return results[:n_recommendations]

    def get_product_details(self, product_scores, reason):
        """Lấy thông tin chi tiết sản phẩm với scoring. product_scores: list[(product_id, score)]."""
        if not product_scores:
            return []
        conn = self.db.connect()
        try:
            results = []
            for product_id, score in product_scores:
                df = pd.read_sql(
                    """
                    SELECT name, category, price, brand, 
                           (SELECT AVG(rating) FROM purchase_history WHERE product_id = ?) as avg_rating
                    FROM products WHERE product_id = ?
                    """,
                    conn, params=[product_id, product_id]
                )
                if not df.empty:
                    results.append({
                        "product_id": product_id,
                        "name": df.iloc[0]["name"],
                        "category": df.iloc[0]["category"],
                        "price": float(df.iloc[0]["price"]),
                        "brand": df.iloc[0]["brand"],
                        "score": float(score),
                        "reason": reason,
                        "avg_rating": float(df.iloc[0]["avg_rating"] or 0),
                    })
            return results
        finally:
            conn.close()

    def get_products_by_ids(self, product_ids, reasons, scores):
        """Lấy thông tin sản phẩm theo danh sách ID (giữ đúng thứ tự đầu vào)."""
        if not product_ids:
            return []
        conn = self.db.connect()
        try:
            placeholders = ",".join(["?"] * len(product_ids))
            df = pd.read_sql(
                f"""
                SELECT product_id, name, category, price, brand
                FROM products
                WHERE product_id IN ({placeholders})
                """,
                conn, params=product_ids
            )
            # Map để trả ra đúng thứ tự product_ids
            info = {int(r["product_id"]): r for _, r in df.iterrows()}
            results = []
            for i, pid in enumerate(product_ids):
                row = info.get(int(pid))
                if not row is None:
                    results.append({
                        "product_id": int(row["product_id"]),
                        "name": row["name"],
                        "category": row["category"],
                        "price": float(row["price"]),
                        "brand": row["brand"],
                        "score": float(scores[i] if i < len(scores) else 1.0),
                        "reason": reasons[i] if i < len(reasons) else "Đề xuất phù hợp",
                    })
            return results
        finally:
            conn.close()

    def recommend_products(self, customer_id, n_recommendations=10, algorithm=None):
        """
        Giao diện chính để gợi ý sản phẩm.
        - TỰ ĐỘNG reset trạng thái khi customer_id thay đổi (đáp ứng yêu cầu của bạn).
        """
        # Reset trạng thái nếu chuyển sang khách hàng mới
        if self._current_customer_id is None or self._current_customer_id != customer_id:
            self._reset_state_for_new_customer(customer_id)

        if algorithm:
            self.set_algorithm(algorithm)

        print(f"🎯 Đang gợi ý cho khách hàng {customer_id} với thuật toán {self.algorithm}...")
        start_time = datetime.now()

        try:
            if self.algorithm == "collaborative":
                results = self.collaborative_filtering(customer_id, n_recommendations)
            elif self.algorithm == "content":
                results = self.content_based_filtering(customer_id, n_recommendations)
            elif self.algorithm == "svd":
                results = self.svd_recommendation(customer_id, n_recommendations)
            elif self.algorithm == "hybrid":
                results = self.hybrid_recommendation(customer_id, n_recommendations)
            else:
                results = self.get_diverse_popular_products(n_recommendations)

            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"✅ Hoàn thành trong {execution_time:.2f}s - Tìm thấy {len(results)} sản phẩm")

            categories = [product["category"] for product in results]
            unique_categories = set(categories)
            print(f"📊 Đa dạng danh mục: {len(unique_categories)}/{len(results)} danh mục khác nhau")

            return results

        except Exception as e:
            print(f"❌ Lỗi trong quá trình gợi ý: {e}")
            return self.get_diverse_popular_products(n_recommendations)


# ---------------------- Test block (tuỳ chọn chạy trực tiếp) ----------------------
if __name__ == "__main__":
    recommender = AdvancedRecommender()
    print("🧪 Testing DIVERSIFIED recommendation system...")

    test_customers = [1, 100, 500]
    algorithms = ["popular", "collaborative", "content", "svd", "hybrid"]

    for customer_id in test_customers:
        print(f"\n{'='*60}")
        print(f"👤 Testing for customer {customer_id}")
        print(f"{'='*60}")

        for algo in algorithms:
            print(f"\n🔍 Algorithm: {algo}")
            recommendations = recommender.recommend_products(customer_id, 5, algo)

            categories = [product["category"] for product in recommendations]
            category_count = len(set(categories))
            print(f"   📈 Đa dạng: {category_count}/5 danh mục")

            for i, product in enumerate(recommendations, 1):
                print(f"  {i}. {product['name']}")
                print(f"     📦 {product['category']} | 🏷️ {product['brand']}")
                print(f"     💰 {product['price']:,.0f} VND | ⭐ {product.get('avg_rating', 'N/A')}")
                print(f"     🎯 {product['reason']}")
                print(f"     📊 Điểm: {product['score']:.3f}")
