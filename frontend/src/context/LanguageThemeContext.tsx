import React, { createContext, useContext, useState, useEffect } from 'react';

export type Language = 'vi' | 'en';
export type BgColor = 'herbal-medicine' | 'radiant-sunrise' | 'classic-amber' | 'deep-ocean';

export interface BgTheme {
  id: BgColor;
  bodyBg: string;
  panelBg: string;
  nameVi: string;
  nameEn: string;
  isLight?: boolean;
  chartLine: string;
  chartFill: string;
}

export const BG_THEMES: Record<BgColor, BgTheme> = {
  'herbal-medicine': {
    id: 'herbal-medicine',
    bodyBg: '#071a14',
    panelBg: '#0f2e24',
    nameVi: 'Xanh Thảo Mộc',
    nameEn: 'Herbal Medicine',
    chartLine: '#2ca97c',
    chartFill: '#2ca97c'
  },
  'radiant-sunrise': {
    id: 'radiant-sunrise',
    bodyBg: '#f8f6f0',
    panelBg: '#ffffff',
    nameVi: 'Bình Minh Rực Rỡ',
    nameEn: 'Radiant Sunrise',
    isLight: true,
    chartLine: '#0d9488',
    chartFill: '#0d9488'
  },
  'classic-amber': {
    id: 'classic-amber',
    bodyBg: '#201108',
    panelBg: '#321b0e',
    nameVi: 'Hổ Phách Cổ Điển',
    nameEn: 'Classic Amber',
    chartLine: '#ab823b',
    chartFill: '#ab823b'
  },
  'deep-ocean': {
    id: 'deep-ocean',
    bodyBg: '#0a182b',
    panelBg: '#122642',
    nameVi: 'Đại Dương Sâu Thẳm',
    nameEn: 'Deep Ocean',
    chartLine: '#3b82f6',
    chartFill: '#3b82f6'
  }
};

const translations = {
  vi: {
    // General
    appName: "YHCT Diamond",
    graphRAGNode: "Nút GraphRAG",
    newChat: "Hội thoại mới",
    queryHistory: "Hành trình truy vấn",
    noHistory: "Chưa có lịch sử",
    options: "Tùy chọn",
    adminDashboard: "Trang Quản Trị",
    encyclopedia: "Bách khoa YHCT",
    clearHistory: "Xóa toàn bộ lịch sử",
    confirmDeleteSession: "Bạn có chắc chắn muốn xóa lịch sử này?",
    confirmClearAll: "⚠️ BẠN CÓ CHẮC CHẮN MUỐN XÓA TOÀN BỘ LỊCH SỬ?",
    logout: "Đăng xuất",
    wallet: "Ví dược liệu",
    walletSub: "Ví dược liệu",
    placeholderChat: "Hỏi chuyên gia về dược liệu, bài thuốc (ví dụ: Ích mẫu, Chỉ thiên...)...",
    send: "Gửi",
    detectedEntity: "Thực thể nhận diện:",
    selectModel: "Chọn mô hình",
    language: "Ngôn ngữ",
    changeBg: "Màu nền",
    backToChat: "Quay lại Chatbot",
    
    // Admin Layout & Header
    adminSection: "Khu vực Quản trị",
    backToChatbot: "Quay lại Chatbot",
    systemOverview: "Tổng quan Hệ thống",
    syncKnowledge: "Đồng bộ Tri thức",
    transactions: "Đối soát Giao dịch",
    userManagement: "Quản lý Tài khoản",
    aiConfig: "Cấu hình AI",

    // Admin Dashboard
    revenueSepay: "Doanh thu SePay",
    realMoney: "Tiền thật đã nạp",
    aiQueries: "Lượt truy vấn AI",
    historyQueries: "Lịch sử hỏi đáp",
    graphEntities: "Thực thể Đồ thị",
    nodesInNeo4j: "Nodes trong Neo4j",
    users: "Người dùng",
    systemAccounts: "Tài khoản hệ thống",
    overviewTitle: "Tổng quan",
    overviewSub: "Giám sát hiệu suất GraphRAG và luồng Fintech thời gian thực.",
    exportReport: "Xuất báo cáo",
    frequencyQueries: "Tần suất Truy vấn AI",
    statisticsQueries: "Thống kê lưu lượng câu hỏi RAG",
    sevenDays: "7 ngày qua",
    thirtyDays: "30 ngày qua",
    recentTrans: "Giao dịch Gần đây",
    invoiceSepay: "Hóa đơn nạp ví SePay",
    noTransactions: "Chưa có giao dịch",
    userPrefix: "Người dùng",
    success: "Thành công",
    pending: "Chờ nạp",

    // Login
    loginSubtitle: "Số hóa tri thức Y học cổ truyền bằng sức mạnh GraphRAG",
    continueWithGoogle: "Tiếp tục với Google",
    redirecting: "Đang chuyển hướng...",
    systemOnline: "HỆ THỐNG GRAPHRAG ĐANG TRỰC TUYẾN",
    privacy: "Bảo mật",
    terms: "Điều khoản",
    dataDeletion: "Xóa dữ liệu",
    support: "Hỗ trợ",
    contact: "Liên hệ",

    // Graph Explorer
    graphTitle: "KHÔNG GIAN TRI THỨC",
    share: "Chia sẻ",
    exportData: "Xuất dữ liệu",
    guidanceTitle: "HƯỚNG DẪN:",
    guidanceZoom: "Scroll để Phóng to/Thu nhỏ",
    guidanceDrag: "Kéo thả các nút để định hình",
    guidanceRealtime: "Dữ liệu cập nhật trực tiếp từ Neo4j Cloud",

    // AI Configuration
    aiConfigTitle: "Cấu hình mô hình AI & Cổng nạp",
    aiParamsTitle: "Tham số Mô hình",
    activeModelLabel: "Mô hình sử dụng",
    temperatureLabel: "Độ sáng tạo (Temperature)",
    qwenUrlLabel: "Qwen Local URL (Ollama)",
    qwenUrlHelp: "Mặc định: http://localhost:11434",
    financeSettingsTitle: "Cấu hình Tài chính & Cước phí",
    exchangeRateLabel: "Mức quy đổi ứng với 1.000 VNĐ:",
    exchangeRateHelp: "Ví dụ: 10000 nghĩa là 1.000 VNĐ = 10.000 Tokens.",
    costPerQueryLabel: "Cước phí mỗi lượt hỏi Chatbot:",
    costPerQueryHelp: "Tương đương khoảng",
    costPerQueryHelpSuffix: "theo tỷ giá nạp hiện tại.",
    rootAdminEmailLabel: "Email Admin Gốc (Root Admin):",
    rootAdminEmailHelp: "Admin gốc có toàn quyền cấp/hạ quyền admin khác và nạp/trừ token trực tiếp.",
    systemPromptLabel: "Chỉ dẫn Hệ thống (System Prompt)",
    apiKeyManagerTitle: "Quản lý danh sách API Key",
    apiKeyManagerHelp: "Nhập trực tiếp API Key vào bảng dưới đây. Nhấn biểu tượng mắt để xem/gõ chuẩn xác.",
    addGeminiFallback: "+ Key Gemini phụ",
    addOpenaiFallback: "+ Key OpenAI phụ",
    unsavedWarning: "Huynh có thay đổi cấu hình hoặc API Key chưa được lưu! Hãy bấm nút 'Xác nhận lưu tất cả' ở dưới hoặc 'Lưu cấu hình' ở đầu trang để áp dụng.",
    providerCol: "Bên / Provider",
    roleCol: "Phân loại",
    keyCol: "Nhập / Chỉnh sửa API Key",
    actionsCol: "Hành động",
    noApiKeys: "Hệ thống chưa có API Key nào được thiết lập. Hãy bấm nút thêm ở trên!",
    confirmSaveAll: "Xác nhận lưu tất cả",
    saveConfig: "Lưu cấu hình",
    loadingConfig: "Đang tải cấu hình...",

    // User Management
    userManagementTitle: "Quản lý người dùng",
    userManagementSub: "Danh sách tài khoản đăng nhập và số dư Token trên hệ thống.",
    searchPlaceholder: "Tìm theo email hoặc tên...",
    rootAdminPanelTitle: "Bảng điều khiển của Admin Gốc (Root Admin)",
    setRoleTitle: "🔑 Thiết lập vai trò qua Email",
    emailToModify: "Email cần sửa:",
    newRole: "Vai trò mới:",
    roleUserOption: "Người dùng (User)",
    roleAdminOption: "Quản trị viên (Admin)",
    updateRoleBtn: "Cập nhật vai trò",
    adjustTokensTitle: "🪙 Điều chỉnh số dư Token qua Email",
    emailToDeposit: "Email cần nạp/trừ:",
    tokenAmountLabel: "Số lượng Token (+ cộng / - trừ):",
    adjustTokensBtn: "Điều chỉnh Token",
    userCol: "Nhân sĩ / Người dùng",
    userRoleCol: "Vai trò",
    tokenBalanceCol: "Số dư Token",
    joinedDateCol: "Ngày tham gia",
    noUsersFound: "Không tìm thấy người dùng nào khớp với từ khóa tìm kiếm.",
    anonymousUser: "Nhân sĩ ẩn danh",
    rootLabel: "Gốc (Root)",
    loadingUsers: "Đang tải danh sách người dùng...",
    unsavedChanges: "Có thay đổi chưa lưu",
    geminiOption: "Google Gemini 2.5 Flash (Tốc độ cao)",
    gpt4oMiniOption: "OpenAI GPT-4o Mini (Khuyên dùng)",
    gpt4oOption: "OpenAI GPT-4o (Cao cấp)",
    vndUnit: "VNĐ",
    hideKey: "Ẩn key",
    showKey: "Hiện key",
    confirmEdit: "Xác nhận sửa",
    cancel: "Hủy bỏ",
    editKey: "Sửa key này",
    deleteKey: "Xóa key này",

    // Landing Page
    landingDocLink: "Chính sách & Tài liệu",
    landingChatBtn: "Vào Chatbot",
    landingLoginBtn: "Đăng nhập",
    landingBadge: "Đại Não Số Hóa Y Học Cổ Truyền Việt Nam",
    landingHeroTitle1: "Khai phá Tri thức",
    landingHeroTitle2: "Y học Cổ truyền",
    landingHeroTitle3: "với AI & Đồ thị",
    landingHeroDesc: "Hệ thống {siteTitle} kết hợp công nghệ GraphRAG hiện đại cùng cơ sở dữ liệu đồ thị Neo4j giúp lập chỉ mục và truy xuất chính xác các thông tin cây thuốc, vị thuốc và bài thuốc cổ phương từ y văn gốc, loại bỏ hoàn toàn hiện tượng ảo giác của các mô hình AI.",
    landingStartBtn: "Bắt đầu Trải nghiệm",
    landingPolicyBtn: "Xem tài liệu chính sách",
    landingFeatureBadge: "Tính năng vượt trội",
    landingFeatureTitle: "Sức mạnh cốt lõi của ",
    landingFeatureSub: "Sự kết hợp hoàn hảo giữa tri thức cổ truyền phong phú và công nghệ trí tuệ nhân tạo hiện đại.",
    landingStepBadge: "Quy trình vận hành",
    landingStepTitle: "Cách thức hoạt động của GraphRAG",
    landingStepSub: "Hệ thống xử lý truy vấn chặt chẽ qua 3 giai đoạn để cho ra kết quả chính xác nhất.",
    landingCtaTitle: "Sẵn sàng khám phá tinh hoa Y học Cổ truyền?",
    landingCtaSub: "Đăng nhập bằng tài khoản Google để hỏi đáp AI về thảo dược, đối sánh các bài thuốc cổ phương và theo dõi đồ thị liên kết.",
    landingCtaBtn: "Trải nghiệm ngay bây giờ",
    landingFooterDesc: "Hệ thống Số hóa và Truy vấn Tri thức Y học Cổ truyền",
    feat1Title: "Ngự Y Kim Cương (GraphRAG)",
    feat1Desc: "Sự kết hợp giữa Graph Database (Neo4j) và mô hình ngôn ngữ lớn giúp chatbot đối chiếu thông tin y văn thực tế, loại bỏ hoàn toàn hiện tượng ảo giác (hallucination) thường gặp ở AI thông thường.",
    feat2Title: "Số hóa Y văn Cổ truyền",
    feat2Desc: "Lập chỉ mục thực thể toàn diện từ bộ sách kinh điển 'Những cây thuốc và vị thuốc Việt Nam' của GS. Đỗ Tất Lợi và các bài thuốc cổ phương quý giá.",
    feat3Title: "Bản đồ Tri thức Tương tác",
    feat3Desc: "Trực quan hóa đồ thị tri thức 2D/3D liên kết chặt chẽ giữa Vị thuốc, Hoạt chất, Tác dụng dược lý, Bộ phận dùng và các Bài thuốc cổ phương.",
    feat4Title: "Bảo mật & Quyền riêng tư",
    feat4Desc: "Cam kết không chia sẻ dữ liệu lịch sử hỏi đáp. Cung cấp công cụ tự phục vụ cho phép người dùng tự xóa sạch toàn bộ dữ liệu lịch sử và tài khoản ngay lập tức.",
    step1Title: "Xử lý Câu hỏi",
    step1Desc: "Bộ xử lý ngôn ngữ tự nhiên (NLU) bóc tách ý định người dùng và tìm kiếm thực thể liên quan.",
    step2Title: "Truy vấn Đồ thị",
    step2Desc: "Lọc và rút trích các thực thể y văn đã được xác thực từ cơ sở dữ liệu đồ thị Neo4j.",
    step3Title: "Sinh phản hồi",
    step3Desc: "Mô hình ngôn ngữ (Gemini/OpenAI) tổng hợp câu trả lời kèm theo nguồn trích dẫn chi tiết (Chương, trang sách).",

    // Policy & Support Layout & Docs
    policyBadge: "Chính sách & Hỗ trợ",
    policyBackBtn: "Quay lại ",
    policyHomeText: "Trang chủ",
    policyChatText: "Chatbot",
    policySidebarTitle: "Danh mục tài liệu",
    policySidebarEdit: "Chỉnh sửa",
    policySidebarEditModalTitle: "Chỉnh sửa Danh mục tài liệu",
    policySidebarLabelPlaceholder: "Tên mục tài liệu",
    policySidebarDescPlaceholder: "Mô tả phụ",
    policySaveBtn: "Lưu thay đổi",
    policySavingBtn: "Đang lưu...",
    policyCancelBtn: "Hủy bỏ",
    policyFooterTitle: "Knowledge Graph",
    policyFooterSub: "Hệ thống Số hóa và Truy vấn Tri thức Y học Cổ truyền bằng GraphRAG",
    policyEditBtn: "Chỉnh sửa trang",
    policyEditingTitle: "Chỉnh sửa trang (Định dạng Markdown)",
    policyLoading: "Đang tải...",
    policyTextTitle: "Chính sách",
    
    // Data Deletion Page
    delTitle: "Yêu cầu xóa dữ liệu",
    delSub: "Chính sách & Công cụ tự phục vụ xóa tài khoản",
    delLoading: "Đang tải...",
    delSuccessPendingTitle: "Yêu cầu đang chờ duyệt...",
    delSuccessPendingDesc: "Yêu cầu xóa tài khoản của bạn đã được gửi đến Admin để phê duyệt. Một email xác nhận đã được gửi đến Admin. Tài khoản và dữ liệu liên quan sẽ bị xóa vĩnh viễn ngay sau khi Admin bấm xác nhận phê duyệt qua email. Bạn sẽ tự động đăng xuất sau giây lát.",
    delSuccessTitle: "Đang xóa dữ liệu...",
    delSuccessDesc: "Hệ thống đang tiến hành xóa toàn bộ dữ liệu cá nhân, lịch sử trò chuyện và giao dịch của bạn khỏi hệ thống {siteTitle}. Dữ liệu sẽ biến mất vĩnh viễn và bạn sẽ được chuyển hướng sau giây lát.",
    delEditTitle: "Chỉnh sửa Quy trình và Cam kết xóa dữ liệu (Markdown)",
    delEditPlaceholder: "Quy trình xóa dữ liệu...",
    delSavePolicyBtn: "Lưu chính sách",
    delUserTitle: "Nhân sĩ YHCT",
    delTokenBalanceLabel: "Số dư hiện tại: {balance} Token (Sẽ bị mất)",
    delUserDesc: "Bạn đang đăng nhập. Bạn có thể gửi yêu cầu xóa tài khoản của mình bằng cách nhấn nút phía dưới. Yêu cầu xóa sẽ được gửi tới Admin phê duyệt qua email trước khi thực hiện xóa vĩnh viễn.",
    delSubmitBtn: "Xóa vĩnh viễn tài khoản của tôi",
    delLoginTitle: "Đăng nhập để xóa tự động",
    delLoginDesc: "Đăng nhập vào hệ thống bằng tài khoản Google bạn muốn xóa. Công cụ tự phục vụ sẽ xuất hiện giúp bạn xóa mọi dữ liệu chỉ trong 1 cú nhấp chuột.",
    delLoginBtn: "Đăng nhập ngay",
    delMailTitle: "Gửi yêu cầu qua Email",
    delMailDesc: "Nếu bạn không thể đăng nhập hoặc gặp sự cố, hãy gửi email trực tiếp tới bộ phận hỗ trợ của chúng tôi để được xử lý thủ công trong vòng 30 ngày.",
    delMailBtn: "Gửi Mail: ",
    delConfirmModalTitle: "Xác nhận xóa tài khoản?",
    delConfirmModalDesc: "Hành động này sẽ xóa vĩnh viễn tài khoản của bạn tại {siteTitle} cùng toàn bộ dữ liệu lịch sử chat, số dư ví token, hóa đơn giao dịch. Bạn sẽ KHÔNG THỂ khôi phục lại dữ liệu này sau khi xóa.",
    delConfirmInputLabel: "Nhập chữ DELETE để xác nhận:",
    delConfirmInputPlaceholder: "DELETE",
    delConfirmBtn: "Xác nhận xóa",
    delProcessingBtn: "Đang xử lý...",
    delConfirmError: "Vui lòng nhập chính xác chữ 'DELETE' để xác nhận!"
  },
  en: {
    // General
    appName: "YHCT Diamond",
    graphRAGNode: "GraphRAG Node",
    newChat: "New Chat",
    queryHistory: "Query History",
    noHistory: "No history yet",
    options: "Options",
    adminDashboard: "Admin Dashboard",
    encyclopedia: "YHCT Wiki",
    clearHistory: "Clear All History",
    confirmDeleteSession: "Are you sure you want to delete this history?",
    confirmClearAll: "⚠️ ARE YOU SURE YOU WANT TO CLEAR ALL HISTORY?",
    logout: "Logout",
    wallet: "Tokens",
    walletSub: "Token Wallet",
    placeholderChat: "Ask experts about herbs, remedies (e.g. Ich mau, Chi thien...)...",
    send: "Send",
    detectedEntity: "Recognized entity:",
    selectModel: "Select model",
    language: "Language",
    changeBg: "Theme Bg",
    backToChat: "Back to Chat",

    // Admin Layout & Header
    adminSection: "Admin Area",
    backToChatbot: "Back to Chatbot",
    systemOverview: "System Overview",
    syncKnowledge: "Knowledge Sync",
    transactions: "Transactions",
    userManagement: "User Management",
    aiConfig: "AI Configuration",

    // Admin Dashboard
    revenueSepay: "SePay Revenue",
    realMoney: "Real money deposited",
    aiQueries: "AI Queries",
    historyQueries: "Q&A history",
    graphEntities: "Graph Entities",
    nodesInNeo4j: "Nodes in Neo4j",
    users: "Total Users",
    systemAccounts: "System accounts",
    overviewTitle: "Overview",
    overviewSub: "Monitor GraphRAG performance and real-time Fintech flow.",
    exportReport: "Export Report",
    frequencyQueries: "AI Query Frequency",
    statisticsQueries: "RAG query volume statistics",
    sevenDays: "Last 7 days",
    thirtyDays: "Last 30 days",
    recentTrans: "Recent Transactions",
    invoiceSepay: "SePay wallet deposit invoices",
    noTransactions: "No transactions yet",
    userPrefix: "User",
    success: "Success",
    pending: "Pending",

    // Login
    loginSubtitle: "Digitizing Traditional Medicine knowledge with GraphRAG",
    continueWithGoogle: "Continue with Google",
    redirecting: "Redirecting...",
    systemOnline: "GRAPHRAG SYSTEM IS ONLINE",
    privacy: "Privacy",
    terms: "Terms",
    dataDeletion: "Data Deletion",
    support: "Support",
    contact: "Contact",

    // Graph Explorer
    graphTitle: "KNOWLEDGE SPACE",
    share: "Share",
    exportData: "Export Data",
    guidanceTitle: "GUIDANCE:",
    guidanceZoom: "Scroll to Zoom In/Out",
    guidanceDrag: "Drag nodes to reshape",
    guidanceRealtime: "Live updates from Neo4j Cloud",

    // AI Configuration
    aiConfigTitle: "AI Model & Gateway Configuration",
    aiParamsTitle: "Model Parameters",
    activeModelLabel: "Active Model",
    temperatureLabel: "Creativity (Temperature)",
    qwenUrlLabel: "Qwen Local URL (Ollama)",
    qwenUrlHelp: "Default: http://localhost:11434",
    financeSettingsTitle: "Finance & Rate Configuration",
    exchangeRateLabel: "Exchange rate per 1,000 VND:",
    exchangeRateHelp: "Example: 10000 means 1,000 VND = 10,000 Tokens.",
    costPerQueryLabel: "Token cost per Chatbot query:",
    costPerQueryHelp: "Equivalent to approx.",
    costPerQueryHelpSuffix: "under current deposit rate.",
    rootAdminEmailLabel: "Root Admin Email:",
    rootAdminEmailHelp: "Root admin has full control to grant/revoke admin status and directly adjust user tokens.",
    systemPromptLabel: "System Instructions (System Prompt)",
    apiKeyManagerTitle: "API Key Directory",
    apiKeyManagerHelp: "Enter API Keys directly in the table below. Click eye icon to view/hide.",
    addGeminiFallback: "+ Add Gemini Fallback",
    addOpenaiFallback: "+ Add OpenAI Fallback",
    unsavedWarning: "You have unsaved changes! Click 'Save settings' or 'Confirm and Save All' to apply.",
    providerCol: "Provider",
    roleCol: "Type",
    keyCol: "Enter / Edit API Key",
    actionsCol: "Actions",
    noApiKeys: "No API Keys configured. Click add buttons above!",
    confirmSaveAll: "Confirm and Save All",
    saveConfig: "Save settings",
    loadingConfig: "Loading configuration...",

    // User Management
    userManagementTitle: "User Accounts",
    userManagementSub: "User logins and token balances.",
    searchPlaceholder: "Search by email or username...",
    rootAdminPanelTitle: "Root Admin Dashboard Controls",
    setRoleTitle: "🔑 Set user role via Email",
    emailToModify: "Email to modify:",
    newRole: "New role:",
    roleUserOption: "User",
    roleAdminOption: "Admin",
    updateRoleBtn: "Update role",
    adjustTokensTitle: "🪙 Adjust tokens via Email",
    emailToDeposit: "Target user email:",
    tokenAmountLabel: "Token amount (+ add / - deduct):",
    adjustTokensBtn: "Adjust tokens",
    userCol: "User / Member",
    userRoleCol: "Role",
    tokenBalanceCol: "Token Balance",
    joinedDateCol: "Joined Date",
    noUsersFound: "No users match the search terms.",
    anonymousUser: "Anonymous User",
    rootLabel: "Root",
    loadingUsers: "Loading users list...",
    unsavedChanges: "Unsaved changes",
    geminiOption: "Google Gemini 2.5 Flash (High Speed)",
    gpt4oMiniOption: "OpenAI GPT-4o Mini (Recommended)",
    gpt4oOption: "OpenAI GPT-4o (Premium)",
    vndUnit: "VND",
    hideKey: "Hide key",
    showKey: "Show key",
    confirmEdit: "Confirm edit",
    cancel: "Cancel",
    editKey: "Edit this key",
    deleteKey: "Delete this key",

    // Landing Page
    landingDocLink: "Policies & Docs",
    landingChatBtn: "Enter Chatbot",
    landingLoginBtn: "Login",
    landingBadge: "Digitized Vietnamese Traditional Medicine Brain",
    landingHeroTitle1: "Explore Traditional",
    landingHeroTitle2: "Medicine Knowledge",
    landingHeroTitle3: "with AI & Graphs",
    landingHeroDesc: "The {siteTitle} system combines modern GraphRAG technology and Neo4j graph database to index and accurately retrieve herbs, remedies, and formulas from original medical literatures, completely eliminating AI hallucinations.",
    landingStartBtn: "Start Experience",
    landingPolicyBtn: "View policy docs",
    landingFeatureBadge: "Key Features",
    landingFeatureTitle: "Core Power of ",
    landingFeatureSub: "The perfect combination of rich traditional knowledge and modern AI technology.",
    landingStepBadge: "How It Works",
    landingStepTitle: "How GraphRAG works",
    landingStepSub: "The system processes queries through 3 strict stages to produce the most accurate results.",
    landingCtaTitle: "Ready to explore the essence of Traditional Medicine?",
    landingCtaSub: "Sign in with Google to ask AI about herbs, match traditional remedies, and trace link graphs.",
    landingCtaBtn: "Start experience now",
    landingFooterDesc: "Traditional Medicine Knowledge Digitization & Query System",
    feat1Title: "Imperial Doctor Diamond (GraphRAG)",
    feat1Desc: "The combination of Graph Database (Neo4j) and Large Language Models helps the chatbot cross-reference actual medical literature, completely eliminating hallucination found in standard AI.",
    feat2Title: "Digitizing Traditional Literature",
    feat2Desc: "Comprehensive entity indexing from the classic book 'Medicinal Plants and Herbs of Vietnam' by Prof. Do Tat Loi and valuable traditional remedies.",
    feat3Title: "Interactive Knowledge Map",
    feat3Desc: "Visualize 2D/3D knowledge graphs showing close relationships between Herbs, Active Ingredients, Pharmacological Effects, Parts Used, and Traditional Formulas.",
    feat4Title: "Security & Privacy",
    feat4Desc: "Committed to not sharing Q&A history. Self-service tools allow users to delete all history and accounts immediately.",
    step1Title: "Query Processing",
    step1Desc: "Natural Language Understanding (NLU) extracts user intent and searches for related entities.",
    step2Title: "Graph Query",
    step2Desc: "Filters and extracts validated medical entities from the Neo4j graph database.",
    step3Title: "Response Generation",
    step3Desc: "Language models (Gemini/OpenAI) synthesize answers with detailed source citations (Chapters, book pages).",

    // Policy & Support Layout & Docs
    policyBadge: "Policies & Support",
    policyBackBtn: "Back to ",
    policyHomeText: "Homepage",
    policyChatText: "Chatbot",
    policySidebarTitle: "Document Directory",
    policySidebarEdit: "Edit",
    policySidebarEditModalTitle: "Edit Document Directory",
    policySidebarLabelPlaceholder: "Document name",
    policySidebarDescPlaceholder: "Sub description",
    policySaveBtn: "Save Changes",
    policySavingBtn: "Saving...",
    policyCancelBtn: "Cancel",
    policyFooterTitle: "Knowledge Graph",
    policyFooterSub: "Traditional Medicine Knowledge Digitization & Query System using GraphRAG",
    policyEditBtn: "Edit page",
    policyEditingTitle: "Edit Page (Markdown Format)",
    policyLoading: "Loading...",
    policyTextTitle: "Policy",

    // Data Deletion Page
    delTitle: "Data Deletion Request",
    delSub: "Policies & Self-Service tools for Account Deletion",
    delLoading: "Loading...",
    delSuccessPendingTitle: "Request pending approval...",
    delSuccessPendingDesc: "Your account deletion request has been sent to the Admin for approval. A confirmation email has been sent to the Admin. The account and related data will be permanently deleted as soon as the Admin confirms approval via email. You will be automatically logged out shortly.",
    delSuccessTitle: "Deleting data...",
    delSuccessDesc: "The system is permanently deleting all your personal data, chat history, and transactions from the {siteTitle} system. Data will be gone forever and you will be redirected shortly.",
    delEditTitle: "Edit Process and Commitment for Data Deletion (Markdown)",
    delEditPlaceholder: "Data deletion process...",
    delSavePolicyBtn: "Save policy",
    delUserTitle: "YHCT Member",
    delTokenBalanceLabel: "Current balance: {balance} Token (Will be lost)",
    delUserDesc: "You are logged in. You can submit your account deletion request by clicking the button below. The request will be sent to the Admin for email approval before permanent deletion.",
    delSubmitBtn: "Permanently delete my account",
    delLoginTitle: "Login to delete automatically",
    delLoginDesc: "Log in to the system using the Google account you want to delete. The self-service tool will appear to help you delete all data in just 1 click.",
    delLoginBtn: "Login now",
    delMailTitle: "Submit Request via Email",
    delMailDesc: "If you cannot log in or encounter issues, send an email directly to our support department for manual processing within 30 days.",
    delMailBtn: "Send Mail: ",
    delConfirmModalTitle: "Confirm account deletion?",
    delConfirmModalDesc: "This action will permanently delete your account at {siteTitle} along with all chat history, token balance, and transaction invoices. You CANNOT recover this data after deletion.",
    delConfirmInputLabel: "Enter the word DELETE to confirm:",
    delConfirmInputPlaceholder: "DELETE",
    delConfirmBtn: "Confirm deletion",
    delProcessingBtn: "Processing...",
    delConfirmError: "Please enter the exact word 'DELETE' to confirm!"
  }
};

export type TranslationKey = keyof typeof translations.vi;

interface LanguageThemeContextType {
  language: Language;
  bgColor: BgColor;
  currentBg: BgTheme;
  t: (key: TranslationKey) => string;
  setLanguage: (lang: Language) => void;
  setBgColor: (color: BgColor) => void;
}

const LanguageThemeContext = createContext<LanguageThemeContextType | undefined>(undefined);

export const LanguageThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLangState] = useState<Language>(() => {
    return (localStorage.getItem('user_lang') as Language) || 'vi';
  });

  const [bgColor, setBgState] = useState<BgColor>(() => {
    const saved = localStorage.getItem('user_bg_theme') as BgColor;
    return (saved && ['herbal-medicine', 'radiant-sunrise', 'classic-amber', 'deep-ocean'].includes(saved)) 
      ? saved 
      : 'herbal-medicine';
  });

  const currentBg = BG_THEMES[bgColor];

  const setLanguage = (lang: Language) => {
    setLangState(lang);
    localStorage.setItem('user_lang', lang);
  };

  const setBgColor = (color: BgColor) => {
    setBgState(color);
    localStorage.setItem('user_bg_theme', color);
  };

  // Sync background and class to <body> tag
  useEffect(() => {
    document.body.style.backgroundColor = currentBg.bodyBg;
    document.documentElement.style.setProperty('--body-bg', currentBg.bodyBg);
    document.documentElement.style.setProperty('--panel-bg', currentBg.panelBg);
    document.documentElement.style.setProperty('--chart-line', currentBg.chartLine);
    document.documentElement.style.setProperty('--chart-fill', currentBg.chartFill);
    if (currentBg.isLight) {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [bgColor, currentBg]);

  // Sync state across multiple tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'user_lang' && e.newValue) {
        setLangState(e.newValue as Language);
      }
      if (e.key === 'user_bg_theme' && e.newValue) {
        setBgState(e.newValue as BgColor);
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const t = (key: TranslationKey): string => {
    return translations[language][key] || translations['vi'][key] || String(key);
  };

  return (
    <LanguageThemeContext.Provider value={{ language, bgColor, currentBg, t, setLanguage, setBgColor }}>
      {children}
    </LanguageThemeContext.Provider>
  );
};

export const useLanguageTheme = () => {
  const context = useContext(LanguageThemeContext);
  if (!context) {
    throw new Error('useLanguageTheme must be used within LanguageThemeProvider');
  }
  return context;
};
