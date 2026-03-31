"""
Module: app/models/base_db.py
Chức năng: Quản lý kết nối cơ sở dữ liệu đồ thị Neo4j.
Nhiệm vụ: 
- Khởi tạo thực thể Neo4jGraph từ thư viện langchain_community.
- Đảm bảo tính duy nhất của kết nối trong suốt vòng đời ứng dụng.
- Xử lý lỗi kết nối và cung cấp phương thức truy vấn an toàn.
"""

from langchain_community.graphs import Neo4jGraph
from app.config import settings

class GraphDB:
    """
    Lớp điều phối kết nối tới Neo4j (Database Wrapper).
    Đảm bảo tuân thủ nguyên tắc Single Responsibility (SRP).
    """

    def __init__(self):
        """
        Khởi tạo thực thể kết nối. 
        Nếu kết nối thành công, tiến hành cập nhật cấu trúc đồ thị (Schema).
        """
        self.graph = self._connect()
        
        # Nếu kết nối thành công, thực hiện làm mới schema thủ công
        if self.graph is not None:
            try:
                # Gọi phương thức nội bộ của LangChain để nạp cấu trúc node/relation
                self.graph.refresh_schema()
                print(f"🔄 [Database] Đã cập nhật Schema cho: {settings.NEO4J_DB_NAME}")
            except Exception as schema_error:
                print(f"⚠️ [Database Warning] Không thể làm mới schema: {str(schema_error)}")

    def _connect(self) -> Neo4jGraph:
        """
        Thực hiện kết nối vật lý tới máy chủ Neo4j.
        Sử dụng thông tin cấu hình tập trung từ Settings.
        
        Returns:
            Neo4jGraph: Đối tượng kết nối của LangChain hoặc None nếu lỗi.
        """
        try:
            # ĐÃ SỬA: Loại bỏ tham số 'refresh_schema' khỏi hàm khởi tạo để tránh lỗi
            instance = Neo4jGraph(
                url=settings.NEO4J_URI,
                username=settings.NEO4J_USER,
                password=settings.NEO4J_PWD,
                database=settings.NEO4J_DB_NAME
            )
            print(f"✅ [Database] Kết nối thành công tới database: {settings.NEO4J_DB_NAME}")
            return instance
        except Exception as e:
            print(f"❌ [Database Error] Lỗi khi khởi tạo driver Neo4j: {str(e)}")
            return None

    def query(self, cypher: str, params: dict = None):
        """
        Thực thi câu lệnh Cypher lên đồ thị.
        
        Args:
            cypher (str): Câu lệnh Cypher cần chạy.
            params (dict, optional): Các tham số truyền vào câu lệnh.
            
        Returns:
            list: Danh sách các record kết quả hoặc mảng rỗng nếu lỗi.
        """
        if self.graph:
            try:
                return self.graph.query(cypher, params=params)
            except Exception as q_error:
                print(f"❌ [Query Error] Lỗi thực thi Cypher: {str(q_error)}")
                return []
        return []

# Khởi tạo instance duy nhất cho toàn hệ thống
# Các module khác chỉ cần gọi: from app.models.base_db import db
db = GraphDB()