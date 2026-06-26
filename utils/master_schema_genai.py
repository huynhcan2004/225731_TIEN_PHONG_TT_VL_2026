from google.genai import types

# =====================================================
# SCHEMA 1: DÙNG CHO STAGE 1 & 2 (FULL CORE)
# =====================================================
RESPONSE_SCHEMA = types.Schema(
    type="OBJECT",
    properties={
        # =====================================================
        # 1️⃣ ENTITY CORE (THỰC THỂ CHÍNH TRONG BÀI VIẾT)
        # =====================================================
        "entity": types.Schema(
            type="OBJECT",
            properties={
                "entity_type": types.Schema(    
                    type="STRING",
                    enum=[
                        "VI_THUOC", "BAI_THUOC", "BENH_LY", 
                        "TRIEU_CHUNG", "HOAT_CHAT", "VI", "TINH", "KINH",
                        "CONG_NANG", "DUOC_LY"
                    ]
                ),
                "id": types.Schema(
                    type="STRING",
                    pattern="^[A-Z0-9_]+$",
                    description="ID chuẩn hóa, viết hoa, không dấu, không prefix"
                ),
                "ten_raw": types.Schema(
                    type="STRING",
                    description="Tên xuất hiện nguyên văn trong tài liệu"
                ),
                "display_name": types.Schema(type="STRING"),
                "ten_khoa_hoc": types.Schema(type="STRING"),
                "ho_thuc_vat": types.Schema(type="STRING"),
                "variants": types.Schema(
                    type="ARRAY",
                    items=types.Schema(type="STRING"),
                    description="Danh sách các tên gọi khác/biến thể. Trả về mảng rỗng [] nếu không có."
                ),
                "properties": types.Schema( 
                    type="OBJECT",
                    properties={
                        "bo_phan_dung": types.Schema(type="STRING"),
                        "phan_bo": types.Schema(type="STRING"),
                        "thu_hai": types.Schema(type="STRING", description="Thời gian và cách thu hái"),
                        "che_bien_tho": types.Schema(type="STRING", description="Cách sơ chế, sấy, phơi ban đầu"),
                        "lieu_dung_chung": types.Schema(type="STRING", description="Số gam hoặc tỷ lệ dùng chung"),
                        "muc_do_doc": types.Schema(type="STRING", description="Độ độc: Bảng A, Bảng B, Có độc, Không độc"),
                        "trieu_chung_ngo_doc": types.Schema(type="STRING", description="Biểu hiện khi ngộ độc hoặc quá liều")
                    }
                )
            },
            required=["entity_type", "id"]
        ),

        # =====================================================
        # 2️⃣ NODES (MẢNG RỖNG - ĐỂ CODE TỰ SINH Ở BƯỚC SAU)
        # =====================================================
        "nodes": types.Schema(
            type="ARRAY",
            description="Bắt buộc để mảng rỗng []. Hệ thống sẽ tự quét relationships để sinh nodes sau.",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "id": types.Schema(type="STRING"),
                    "label": types.Schema(
                        type="STRING",
                        enum=[
                            "ViThuoc", "BaiThuoc", "BenhLy", 
                            "TrieuChung", "HoatChat", "DoiTuong", "Kinh", "Tinh", "Vi",
                            "CongNang", "DuocLy", "NhomBenh"
                        ]
                    ),
                    "properties": types.Schema(
                        type="OBJECT",
                        properties={
                            "aliases": types.Schema(
                                type="ARRAY", 
                                items=types.Schema(type="STRING")
                            )
                        }
                    )
                },
                required=["id", "label"]
            )
        ),

        # =====================================================
        # 3️⃣ CLAIMS (ĐẶC TÍNH YHCT DỰA TRÊN Y VĂN)
        # =====================================================
        "claims": types.Schema(
            type="ARRAY",
            description="Danh sách các claim. Trả về mảng rỗng [] nếu không có dữ liệu trích xuất.",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "source": types.Schema(
                        type="OBJECT",
                        properties={
                            "source_id": types.Schema(type="STRING"),
                            "ten_sach": types.Schema(type="STRING"),
                            "tac_gia": types.Schema(type="STRING"),
                            "nam_xuat_ban": types.Schema(type="INTEGER"),
                            "trang": types.Schema(type="STRING")
                        },
                        required=["source_id", "ten_sach"]
                    ),
                    "dac_tinh_yhct": types.Schema(
                        type="OBJECT",
                        properties={
                            "vi": types.Schema(
                                type="ARRAY",
                                items=types.Schema(
                                    type="STRING",
                                    enum=["Cay (Tân)", "Chua (Toan)", "Đắng (Khổ)", "Ngọt (Cam)", "Mặn (Hàm)", "Nhạt (Đạm)"]
                                )
                            ),
                            "tinh": types.Schema(
                                type="STRING",
                                enum=["Hàn", "Đại hàn", "Hơi hàn", "Lương", "Bình", "Hơi ôn", "Ôn", "Nhiệt", "Đại nhiệt"]
                            ),
                            "quy_kinh": types.Schema(
                                type="ARRAY",
                                items=types.Schema(type="STRING")
                            ),
                            "cong_nang": types.Schema(type="STRING"),
                            "kieng_ky_dac_biet": types.Schema(type="STRING")
                        }
                    ),
                    "mo_ta_theo_nguon": types.Schema(
                        type="OBJECT",
                        properties={
                            "hinh_thai_chi_tiet": types.Schema(type="STRING"),
                            "thanh_phan_hoa_hoc": types.Schema(
                                type="ARRAY",
                                items=types.Schema(type="STRING")
                            ),
                            "lieu_dung_tong_quat": types.Schema(type="STRING"),
                            "ghi_chu_bo_sung": types.Schema(type="STRING"),
                            "cach_dung_bao_che": types.Schema(type="STRING")
                        }
                    ),
                    "confidence_score": types.Schema(type="NUMBER", nullable=True)
                },
                required=["source"]
            )
        ),

        # =====================================================
        # 4️⃣ RELATIONSHIPS (QUAN HỆ GIỮA CÁC NODE)
        # =====================================================
        "relationships": types.Schema(
            type="ARRAY",
            description="Danh sách các quan hệ. BẮT BUỘC trả về mảng rỗng [] nếu văn bản không có thông tin.",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "from": types.Schema(type="STRING"),
                    "to": types.Schema(type="STRING"),
                    "relation_type": types.Schema(
                        type="STRING",
                        enum=[
                            "THAN_PHAN_CUA", "BAO_GOM_VI_THUOC", "CO_TRONG_BAI_THUOC",
                            "CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG", "LIEN_QUAN_TRIEU_CHUNG",
                            "CO_CHUA_HOAT_CHAT", "CO_VI", "CO_TINH", "QUY_KINH",
                            "KIENG_KY_BENH", "KIENG_KY_TRIEU_CHUNG", "KIENG_KY_CHO",
                            "PHOI_HOP_VOI", "CO_CONG_NANG", "CO_TAC_DUNG_DUOC_LY", "THUOC_NHOM_BENH"
                        ]
                    ),
                    "source": types.Schema(
                        type="OBJECT",
                        properties={
                            "source_id": types.Schema(type="STRING"),
                            "ten_sach": types.Schema(type="STRING"),
                            "trang": types.Schema(type="STRING")
                        },
                        required=["source_id"]
                    ),
                    "properties": types.Schema(
                        type="OBJECT",
                        properties={
                            "loai_remedy": types.Schema(
                                type="STRING", 
                                enum=["Đơn phương", "Đa phương", "Chưa rõ"],
                                description="Phân loại bài thuốc"
                            ),
                            "loai_che_pham": types.Schema(
                                type="STRING",
                                enum=["Dân gian", "Cổ phương", "Chuẩn hóa hiện đại", "Chưa rõ"],
                                description="Hình thức chế phẩm"
                            ),
                            "doi_tuong_thu_huong": types.Schema(
                                type="STRING",
                                description="Dùng cho Người hay Thú y (Trâu, Bò, Gà...). Mặc định là Người."
                            ),
                            "ap_dung_cho_loai": types.Schema(
                                type="STRING",
                                description="Phân loại tên loài thực vật cụ thể áp dụng (Nếu có nhiều loài)"
                            ),
                            "lieu_luong": types.Schema(type="STRING", description="Số gam hoặc tỷ lệ"),
                            "vai_tro": types.Schema(
                                type="STRING",
                                enum=["Quân", "Thần", "Tá", "Sứ", "Chưa rõ"],
                                description="Vai trò y lý trong bài thuốc"
                            ),
                            "phoi_ngu_logic": types.Schema(type="STRING"),
                            "mo_ta_chi_tiet": types.Schema(type="STRING"),
                            "ghi_chu": types.Schema(type="STRING"),

                        }
                    ),
                    "confidence_score": types.Schema(type="NUMBER", nullable=True)
                },
                # 🟢 ĐÃ FIX LỆCH PHA: Xóa "source" khỏi required để AI không bị mâu thuẫn với lệnh cấm trong Prompt
                required=["from", "to", "relation_type"]
            )
        )
    },
    required=["entity", "nodes", "relationships"]
)

# =====================================================
# SCHEMA 2: SIÊU NHẸ - DÙNG CHO STAGE 3 & 4
# Được bọc trong OBJECT để tương thích với model_dump()
# =====================================================
STAGE34_SCHEMA = types.Schema(
    # 🟢 ĐÃ FIX LỆCH PHA: Chuyển Root thành OBJECT để không làm crash code `hasattr(parsed, 'model_dump')`
    type="OBJECT",
    properties={
        "relationships": types.Schema(
            type="ARRAY",
            description="Chỉ xuất danh sách các quan hệ. BẮT BUỘC trả về mảng rỗng [] nếu không tìm thấy.",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "from": types.Schema(type="STRING"),
                    "to": types.Schema(type="STRING"),
                    "relation_type": types.Schema(
                        type="STRING",
                        enum=[
                            "THAN_PHAN_CUA", "BAO_GOM_VI_THUOC", "CO_TRONG_BAI_THUOC",
                            "CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG", "LIEN_QUAN_TRIEU_CHUNG",
                            "CO_CHUA_HOAT_CHAT", "CO_VI", "CO_TINH", "QUY_KINH",
                            "KIENG_KY_BENH", "KIENG_KY_TRIEU_CHUNG", "KIENG_KY_CHO",
                            "PHOI_HOP_VOI", "CO_CONG_NANG", "CO_TAC_DUNG_DUOC_LY", "THUOC_NHOM_BENH"
                        ]
                    ),
                    "properties": types.Schema(
                        type="OBJECT",
                        properties={
                            "loai_remedy": types.Schema(type="STRING", enum=["Đơn phương", "Đa phương", "Chưa rõ"]),
                            "loai_che_pham": types.Schema(type="STRING", enum=["Dân gian", "Cổ phương", "Chuẩn hóa hiện đại", "Chưa rõ"]),
                            "doi_tuong_thu_huong": types.Schema(type="STRING"),
                            "ap_dung_cho_loai": types.Schema(type="STRING"),
                            "lieu_luong": types.Schema(type="STRING"),
                            "vai_tro": types.Schema(type="STRING", enum=["Quân", "Thần", "Tá", "Sứ", "Chưa rõ"]),
                            "phoi_ngu_logic": types.Schema(type="STRING"),
                            "mo_ta_chi_tiet": types.Schema(type="STRING"),
                            "cach_dung": types.Schema(type="STRING"),
                            "ghi_chu": types.Schema(type="STRING")
                        }
                    )
                },
                required=["from", "to", "relation_type"]
            )
        )
    },
    required=["relationships"]
)