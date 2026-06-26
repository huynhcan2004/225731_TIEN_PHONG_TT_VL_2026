"""
╔══════════════════════════════════════════════════════════════════╗
║  ULTIMATE NEO4J CLOUD RAG LOADER (DEEP DEPLOY TO AURA DB)       ║
║  Chức năng: Xóa sạch CSDL đám mây cũ, nạp dữ liệu vào Server.     ║
║  HOTFIX MÂY 1: Cấu hình chuẩn xác tài khoản xác thực AuraDB.    ║
║  HOTFIX MÂY 2: Bắt buộc ép DB_NAME về 'neo4j' (Chuẩn bản Free). ║
║  HOTFIX MÂY 3: Giảm tải Batch Size để tránh Timeout mạng đám mây.║
║  HOTFIX MÂY 4: Đổi giao thức sang bolt+s để sửa lỗi định tuyến.  ║
║  HOTFIX MÂY 5: Thêm Keep-Alive chống rớt gói tin mạng Internet.  ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import glob
import os
import time
from neo4j import GraphDatabase
import ollama  
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import settings

# ==========================================================
# 1. CẤU HÌNH KẾT NỐI TRỰC TIẾP LÊN MÁY CHỦ NEO4J CLOUD (AURA)
# ==========================================================
# Đã đổi giao thức thành bolt+s để tránh lỗi "Unable to retrieve routing information"
URI = settings.NEO4J_URI
USER = settings.NEO4J_USER
PWD = settings.NEO4J_PWD

# ⚠️ LƯU Ý QUAN TRỌNG: Gói Neo4j AuraDB Free KHÔNG hỗ trợ đa cơ sở dữ liệu.
# Bắt buộc phải trỏ về cơ sở dữ liệu mặc định hệ thống tên là "neo4j".
DB_NAME = settings.NEO4J_DB_NAME 

# Đường dẫn thư mục dữ liệu
INPUT_DIR = settings.DIR_GOLD_LINKED 
CACHE_PATH = "config/checkpoints/embeddings_cache_bgem3.json" 

os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

# Sử dụng mô hình nhúng bge-m3 qua Ollama local (1024 chiều)
EMBEDDING_MODEL_NAME = 'bge-m3'
VECTOR_DIMENSIONS = 1024  

class Neo4jAuraUploader:
    def __init__(self, uri, user, password):
        # Ép cấu hình giữ kết nối sống (Keep-Alive) chống nghẽn mạng đám mây khi nạp số lượng lớn
        self.driver = GraphDatabase.driver(
            uri, 
            auth=(user, password),
            max_connection_lifetime=30 * 60, # 30 phút
            keep_alive=True
        )
        self.session_kwargs = {}
        if DB_NAME and DB_NAME != "neo4j":
            self.session_kwargs["database"] = DB_NAME

    def close(self):
        self.driver.close()

    def clear_database(self):
        """XÓA SẠCH DỮ LIỆU CŨ TRÊN MÂY (TỐI ƯU TRANSACTIONS)"""
        print("🧹 Đang tiến hành dọn dẹp Cơ sở dữ liệu Neo4j Aura Cloud...")
        with self.driver.session(**self.session_kwargs) as session:
            # 1. Xóa Nút và Cạnh theo lô nhỏ hơn để tránh nghẽn băng thông mạng Internet
            try:
                session.run("CALL { MATCH (n) DETACH DELETE n } IN TRANSACTIONS OF 5000 ROWS")
                print("   -> Đã xóa sạch toàn bộ Thực thể và Quan hệ cũ trên đám mây.")
            except Exception:
                try:
                    session.run("MATCH (n) DETACH DELETE n")
                    print("   -> Đã xóa sạch dữ liệu bằng cơ chế Standard Delete.")
                except Exception as ex:
                    print(f"   -> Lỗi khi dọn dẹp dữ liệu: {ex}")
            
            # 2. Xóa các Index cũ để tạo không gian cho mô hình 1024 chiều mới
            try:
                session.run("DROP INDEX entity_vector_index")
                print("   -> Đã xóa Vector Index cũ thành công.")
            except Exception: pass

            try:
                session.run("DROP INDEX entity_search_index")
                print("   -> Đã xóa Full-text Index cũ thành công.")
            except Exception: pass

    def setup_indexes(self):
        """Thiết lập các Index mỏ neo sự thật trực tiếp trên AuraDB"""
        print(f"⚡ Đang thiết lập Hệ thống Index mới ({VECTOR_DIMENSIONS} chiều) lên Server...")
        with self.driver.session(**self.session_kwargs) as session:
            # Ràng buộc Unique ID thực thể
            try:
                session.run("CREATE CONSTRAINT thucthe_id_unique IF NOT EXISTS FOR (n:ThucThe) REQUIRE n.id IS UNIQUE")
            except Exception as e: print(f" - Note Constraint: {e}")

            # Thiết lập Full-text Search Index hỗ trợ chatbot tra cứu mờ tiếng Việt
            try:
                session.run("""
                CREATE FULLTEXT INDEX entity_search_index IF NOT EXISTS 
                FOR (n:ThucThe) ON EACH [n.canonical_name, n.aliases]
                """)
            except Exception as e: print(f" - Note Fulltext: {e}")

            # Tạo không gian Vector Index so khớp khoảng cách tương đồng Cosine
            try:
                session.run(f"""
                CREATE VECTOR INDEX entity_vector_index IF NOT EXISTS
                FOR (n:ThucThe) ON (n.embedding)
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {VECTOR_DIMENSIONS},
                    `vector.similarity_function`: 'cosine'
                }}}}
                """)
            except Exception as e: print(f" - Note Vector Index: {e}")
        print("✅ Đã khởi tạo thành công nền tảng Index đám mây!")

    def upload_global_graph(self, nodes_list, rels_list):
        """Bơm dữ liệu siêu đồ thị lên mây sử dụng Batching tối ưu băng thông mạng"""
        print(f"🚀 Tiến hành đẩy {len(nodes_list)} Thực thể và {len(rels_list)} Quan hệ lên Server...")
        
        with self.driver.session(**self.session_kwargs) as session:
            # --- NẠP NODES HÀNG LOẠT (BATCH SIZE = 500 ĐỂ TRÁNH TIMEOUT MẠNG INTERNET) ---
            batch_size = 500  
            for i in range(0, len(nodes_list), batch_size):
                batch = nodes_list[i:i+batch_size]
                session.run("""
                UNWIND $nodes AS node
                MERGE (n:ThucThe {id: node.id})
                SET n += node.properties
                WITH n, node
                CALL apoc.create.setLabels(n, ['ThucThe', node.label]) YIELD node as labeledNode
                RETURN count(*)
                """, nodes=batch)
                print(f"   -> Đã đẩy Nodes lô {i//batch_size + 1} thành công.")

            # --- NẠP QUAN HỆ CẠNH (RELATIONSHIPS BATCH SIZE = 1000) ---
            rel_batch_size = 1000  
            for i in range(0, len(rels_list), rel_batch_size):
                batch = rels_list[i:i+rel_batch_size]
                session.run("""
                UNWIND $rels AS rel
                MATCH (a:ThucThe {id: rel.from})
                MATCH (b:ThucThe {id: rel.to})
                CALL apoc.merge.relationship(a, rel.relation_type, {}, rel.properties, b, {}) YIELD rel as r
                RETURN count(*)
                """, rels=batch)
                print(f"   -> Đã nối Quan hệ cạnh lô {i//rel_batch_size + 1} thành công.")

# ==========================================================
# 🧠 TRÌNH TIỀN XỬ LÝ (PRE-PROCESSOR) & EMBEDDING CACHE
# ==========================================================
def process_and_embed_data(input_dir):
    files = glob.glob(os.path.join(input_dir, "*.json"))
    if not files:
        print(f"❌ LỖI: Không tìm thấy tệp JSON nào tại đường dẫn: {input_dir}")
        return [], []

    global_nodes = {}  
    global_rels = {}   

    print(f"🔍 Quét tìm thấy {len(files)} tệp tin tri thức. Đang gom cấu trúc dữ liệu...")

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta_richness = 0.0
        meta_reliability = 0.0
        if "metadata" in data and "scientific_metrics" in data["metadata"]:
            metrics = data["metadata"]["scientific_metrics"]
            meta_richness = float(metrics.get("data_richness_index", 0.0))
            meta_reliability = float(metrics.get("reliability_c_score", 0.0))

        main_entity_id = data.get("entity", {}).get("id", "")

        for node in data.get("nodes", []):
            nid = node["id"]
            if nid == main_entity_id:
                if "properties" not in node:
                    node["properties"] = {}
                node["properties"]["data_richness_index"] = meta_richness
                node["properties"]["reliability_c_score"] = meta_reliability

            if nid not in global_nodes:
                global_nodes[nid] = node
            else:
                for k, v in node.get("properties", {}).items():
                    if v and not global_nodes[nid]["properties"].get(k):
                        global_nodes[nid]["properties"][k] = v

        for rel in data.get("relationships", []):
            edge_key = (rel["from"], rel["relation_type"], rel["to"])
            if "properties" not in rel:
                rel["properties"] = {}
                
            rel["properties"]["from_name"] = global_nodes.get(rel["from"], {}).get("properties", {}).get("canonical_name", "Unknown")
            rel["properties"]["to_name"] = global_nodes.get(rel["to"], {}).get("properties", {}).get("canonical_name", "Unknown")

            if "confidence_score" in rel:
                rel["properties"]["confidence_score"] = float(rel["confidence_score"])
            
            if edge_key not in global_rels:
                global_rels[edge_key] = rel
            else:
                old_desc = str(global_rels[edge_key]["properties"].get("mo_ta_chi_tiet", ""))
                new_desc = str(rel["properties"].get("mo_ta_chi_tiet", ""))
                if new_desc and new_desc not in old_desc:
                    global_rels[edge_key]["properties"]["mo_ta_chi_tiet"] = (old_desc + " | " + new_desc).strip(" | ")
                
                old_score = global_rels[edge_key]["properties"].get("confidence_score", 0.0)
                new_score = rel["properties"].get("confidence_score", 0.0)
                if new_score > old_score:
                    global_rels[edge_key]["properties"]["confidence_score"] = new_score

    print(f"📊 Thu hoạch thành công: {len(global_nodes)} Nodes và {len(global_rels)} Cạnh quan hệ.")
    
    print("🧬 Đang sinh Chữ ký ngữ cảnh từ các cạnh liên kết...")
    node_context = {nid: "" for nid in global_nodes.keys()}

    for rel in global_rels.values():
        frm = rel["from"]
        to = rel["to"]
        rel_type = rel["relation_type"]
        from_name = rel["properties"]["from_name"]
        to_name = rel["properties"]["to_name"]
        
        if rel_type == "CHU_TRI_BENH":
            node_context[frm] += f" Chủ trị bệnh: {to_name}."
            if to in node_context: node_context[to] += f" Được điều trị bởi vị thuốc: {from_name}."
        elif rel_type == "CO_CHUA_HOAT_CHAT":
            node_context[frm] += f" Thành phần chứa: {to_name}."
            if to in node_context: node_context[to] += f" Tìm thấy trong cây: {from_name}."
        elif rel_type == "CO_CONG_NANG":
            node_context[frm] += f" Có công năng: {to_name}."
        elif rel_type == "CO_VI":
            node_context[frm] += f" Vị của thuốc: {to_name}."
        elif rel_type == "CO_TINH":
            node_context[frm] += f" Tính của thuốc: {to_name}."
        elif rel_type == "BAO_GOM_VI_THUOC":
            node_context[frm] += f" Bài thuốc chứa: {to_name}."
            if to in node_context: node_context[to] += f" Dùng trong bài thuốc: {from_name}."

    # Xử lý Đọc ghi bộ nhớ đệm Cache Vector
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
            print(f"💽 Đã khôi phục {len(cache)} định dạng Vectors từ Cache BGE-M3.")

    nodes_list = list(global_nodes.values())
    rels_list = list(global_rels.values())
    
    print(f"🤖 Đang nhúng mô hình ngôn ngữ chuyên sâu qua Ollama [{EMBEDDING_MODEL_NAME}]...")
    new_embeddings_count = 0
    
    for i, node in enumerate(nodes_list):
        nid = node["id"]
        if nid in cache:
            node["properties"]["embedding"] = cache[nid]
            continue

        name = node.get("properties", {}).get("canonical_name", "")
        aliases = node.get("properties", {}).get("aliases", [])
        aliases_str = ", ".join(aliases) if isinstance(aliases, list) else str(aliases)
        label_vn = node.get("label", "ThucThe")
        search_vector_hint = node.get("properties", {}).get("search_vector_hint", "")
        raw_desc = str(node.get("properties", {}).get("che_bien_tho", "") or node.get("properties", {}).get("mo_ta_chi_tiet", "") or "")
        extra_info = node_context.get(nid, "").strip()
        
        text_to_embed = (
            f"Thực thể YHCT: {name}. "
            f"Phân loại: {label_vn}. "
            f"Tên gọi khác: {aliases_str}. "
            f"Định nghĩa & Gợi ý tìm kiếm: {search_vector_hint} "
            f"Đặc điểm lâm sàng & Quan hệ: {extra_info} "
            f"Mô tả cơ bản: {raw_desc[:250]}"
        ).strip()
        
        try:
            response = ollama.embeddings(model=EMBEDDING_MODEL_NAME, prompt=text_to_embed)
            node["properties"]["embedding"] = response["embedding"]
            cache[nid] = response["embedding"]
            new_embeddings_count += 1
            
            if new_embeddings_count % 50 == 0:
                print(f"   ... Đã nhúng mới thành công {new_embeddings_count} thực thể.")
                
        except Exception as e:
            raise RuntimeError(f"❌ Lỗi kết nối Ollama: Hãy chắc chắn Ollama đang chạy dưới local và đã chạy lệnh 'ollama pull {EMBEDDING_MODEL_NAME}': {e}")

    if new_embeddings_count > 0:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"💾 Đã cập nhật {new_embeddings_count} vector mới vào bộ đệm cache.")
    else:
        print("⚡ Hoàn hảo! Toàn bộ thực thể đã được tái sử dụng qua Cache. Không tốn tài nguyên nhúng thô!")

    return nodes_list, rels_list

# ==========================================================
# ⚡ KÍCH HOẠT ĐƯỜNG ỐNG PIPELINE LÊN SERVER CLOUD
# ==========================================================
def run_pipeline_deploy():
    print(f"💎 BẮT ĐẦU TRUYỀN DỮ LIỆU: Wipe & Reload Siêu Đồ thị vào Neo4j Aura Cloud")
    
    # Kiểm tra trạng thái hoạt động của dịch vụ Ollama local
    try:
        ollama.list()
    except Exception:
        print("❌ LỖI HỆ THỐNG: Không thể thiết lập kết nối tới Ollama. Vui lòng mở ứng dụng Ollama!")
        return

    start_time = time.time()
    
    # 1. Thu thập dữ liệu và chuyển đổi không gian vector 1024 chiều
    nodes_list, rels_list = process_and_embed_data(INPUT_DIR)
    
    if not nodes_list:
        print("❌ Hủy bỏ tiến trình: Hồ chứa dữ liệu Nodes trống.")
        return

    # 2. Khởi tạo tác tử kết nối đẩy dữ liệu trực tiếp lên mây
    uploader = Neo4jAuraUploader(URI, USER, PWD)
    uploader.clear_database()
    uploader.setup_indexes()
    
    try:
        uploader.upload_global_graph(nodes_list, rels_list)
        duration = round(time.time() - start_time, 2)
        print(f"\n🏆 TRIỂN KHAI THÀNH CÔNG! Đồ thị đám mây vKG đã sẵn sàng phục vụ Web/App Android.")
        print(f"⏱ Tổng thời gian đồng bộ Internet: {duration} giây.")
    except Exception as e:
        print(f"❌ Thất bại khi nạp dữ liệu lên đám mây AuraDB: {e}")
        print("💡 Gợi ý xử lý: Kiểm tra lại plugin APOC hoặc quyền ghi của gói Free Instance.")
    finally:
        uploader.close()

if __name__ == "__main__":
    run_pipeline_deploy()