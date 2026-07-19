import React, { useState, useEffect, useRef } from "react";
import {
  LayoutDashboard, FileText, Scale, BookMarked,
  Upload, Search, ChevronDown, X, AlertTriangle,
  MessageSquare, Send, ChevronRight, Calendar,
  Building2, LogOut, Bell, Loader2, AlertCircle,
  Brain, Plus, ExternalLink, ChevronLeft, GitBranch,
  Download, Network, ArrowRight, Eye, Share2,
  Lightbulb, CheckCircle2, Link, ZoomIn, ZoomOut,
  Maximize2, Copy, Mail, Users, Lock, BookOpen, Hash,
  User, Phone, MapPin, Save, FileUp, GripVertical, Briefcase, Layers,
} from "lucide-react";
import {
  askLegacyDocument,
  loadLegacyGraph,
  loadLegacyKnowledgeTerms,
  loadLegacyPortalData,
  uploadLegacyDocument,
  type LegacyDocument,
  type LegacyKnowledgeTerm,
  type LegacyLaw,
  type LegacyTreeNode,
} from "../legacy-ui-api";
import { changePassword, type UserPublic } from "../api";

// ─── TYPES ───────────────────────────────────────────────────────────────────

type Screen = "login" | "dashboard" | "documents" | "library" | "notebook" | "processing" | "tree";

type DocNode = LegacyTreeNode;

interface ImportData {
  ten: string;
  chucVu: string;
  phongBan: string;
  thon: string;
  xa: string;
  tinh: string;
  baoCaoFile: string | null;
  vanBanFile: string | null;
}

// ─── DATA ────────────────────────────────────────────────────────────────────

let MY_DOCUMENTS: LegacyDocument[] = [];

let LEGAL_LIBRARY: LegacyLaw[] = [];

const LAW_DETAILS: Record<number, { description: string; chapters: { title: string; summary: string }[]; relatedIds: number[]; keywords: string[] }> = {
  1: {
    description: "Bộ luật Dân sự 2015 quy định địa vị pháp lý, chuẩn mực pháp lý về cách ứng xử của cá nhân, pháp nhân; quyền, nghĩa vụ về nhân thân và tài sản của cá nhân, pháp nhân trong các quan hệ được hình thành trên cơ sở bình đẳng, tự do ý chí, độc lập về tài sản và tự chịu trách nhiệm.",
    chapters: [
      { title: "Phần thứ nhất: Quy định chung", summary: "Nguyên tắc cơ bản của pháp luật dân sự, xác lập, thực hiện và bảo vệ quyền dân sự." },
      { title: "Phần thứ hai: Pháp nhân", summary: "Điều kiện, phân loại, thành lập, hoạt động và giải thể pháp nhân." },
      { title: "Phần thứ ba: Tài sản và quyền sở hữu", summary: "Quyền sở hữu, các hình thức sở hữu và căn cứ xác lập, chấm dứt quyền sở hữu." },
      { title: "Phần thứ tư: Nghĩa vụ và hợp đồng", summary: "Các loại nghĩa vụ dân sự, hợp đồng, bồi thường thiệt hại ngoài hợp đồng." },
      { title: "Phần thứ năm: Thừa kế", summary: "Quyền thừa kế, thừa kế theo di chúc và thừa kế theo pháp luật." },
      { title: "Phần thứ sáu: Quan hệ dân sự có yếu tố nước ngoài", summary: "Nguyên tắc áp dụng pháp luật đối với quan hệ dân sự có yếu tố nước ngoài." },
    ],
    relatedIds: [2, 5, 8],
    keywords: ["pháp nhân", "hợp đồng", "quyền sở hữu", "thừa kế", "bồi thường thiệt hại"],
  },
  2: {
    description: "Luật Doanh nghiệp 2020 quy định về thành lập, tổ chức quản lý, tổ chức lại, giải thể và hoạt động của doanh nghiệp, bao gồm công ty TNHH, công ty cổ phần, công ty hợp danh và doanh nghiệp tư nhân trên lãnh thổ Việt Nam.",
    chapters: [
      { title: "Chương I: Quy định chung", summary: "Phạm vi điều chỉnh, đối tượng áp dụng và các khái niệm cơ bản." },
      { title: "Chương II: Thành lập doanh nghiệp", summary: "Điều kiện, hồ sơ, trình tự đăng ký thành lập doanh nghiệp." },
      { title: "Chương III: Công ty TNHH", summary: "Cơ cấu tổ chức, quyền và nghĩa vụ của thành viên công ty TNHH." },
      { title: "Chương IV: Công ty cổ phần", summary: "Phát hành cổ phần, quyền cổ đông, cơ cấu quản trị công ty cổ phần." },
      { title: "Chương V: Tổ chức lại doanh nghiệp", summary: "Hợp nhất, sáp nhập, chia, tách và chuyển đổi loại hình doanh nghiệp." },
    ],
    relatedIds: [1, 3, 7],
    keywords: ["công ty TNHH", "công ty cổ phần", "cổ đông", "thành viên góp vốn", "vốn điều lệ"],
  },
  3: {
    description: "Luật Đấu thầu 2023 quy định quản lý nhà nước về đấu thầu; trách nhiệm của các bên trong hoạt động đấu thầu; lựa chọn nhà thầu, nhà đầu tư thực hiện dự án đầu tư kinh doanh.",
    chapters: [
      { title: "Chương I: Quy định chung", summary: "Phạm vi, đối tượng áp dụng và nguyên tắc cơ bản trong đấu thầu." },
      { title: "Chương II: Kế hoạch lựa chọn nhà thầu", summary: "Lập, thẩm định và phê duyệt kế hoạch lựa chọn nhà thầu." },
      { title: "Chương III: Hình thức và phương thức lựa chọn nhà thầu", summary: "Đấu thầu rộng rãi, đấu thầu hạn chế, chỉ định thầu và mua sắm trực tiếp." },
      { title: "Chương IV: Quy trình lựa chọn nhà thầu", summary: "Chuẩn bị, phát hành hồ sơ mời thầu, đánh giá và xét duyệt trúng thầu." },
      { title: "Chương V: Thực hiện hợp đồng", summary: "Ký kết, quản lý, thanh lý hợp đồng sau đấu thầu." },
    ],
    relatedIds: [4, 6, 1],
    keywords: ["đấu thầu rộng rãi", "chỉ định thầu", "nhà thầu", "hồ sơ mời thầu", "E-HSMT"],
  },
  4: {
    description: "Nghị định 24/2024/NĐ-CP quy định chi tiết về quản lý dự án đầu tư xây dựng, bổ sung và hướng dẫn thi hành Luật Xây dựng trong bối cảnh mới.",
    chapters: [
      { title: "Chương I: Quy định chung", summary: "Phạm vi điều chỉnh và các khái niệm liên quan đến dự án xây dựng." },
      { title: "Chương II: Lập và thẩm định dự án", summary: "Nội dung báo cáo nghiên cứu khả thi và quy trình thẩm định." },
      { title: "Chương III: Thiết kế xây dựng", summary: "Các bước thiết kế, thẩm định và phê duyệt thiết kế công trình." },
      { title: "Chương IV: Thi công xây dựng", summary: "Điều kiện khởi công, giám sát và kiểm tra chất lượng công trình." },
    ],
    relatedIds: [6, 3, 1],
    keywords: ["chủ đầu tư", "tổng thầu", "giám sát thi công", "nghiệm thu", "báo cáo giám sát"],
  },
  5: {
    description: "Thông tư 03/2023/TT-BTC quy định về chế độ kế toán áp dụng cho các tổ chức hoạt động trong lĩnh vực thuế và các đơn vị liên quan (đã hết hiệu lực từ 01/01/2025).",
    chapters: [
      { title: "Chương I: Quy định chung", summary: "Phạm vi, đối tượng áp dụng và nguyên tắc kế toán thuế." },
      { title: "Chương II: Tài khoản kế toán", summary: "Danh mục và nội dung các tài khoản kế toán áp dụng." },
      { title: "Chương III: Báo cáo tài chính", summary: "Mẫu biểu, nội dung và kỳ lập báo cáo tài chính." },
    ],
    relatedIds: [8, 2, 1],
    keywords: ["tài khoản kế toán", "báo cáo tài chính", "chứng từ kế toán", "sổ kế toán"],
  },
  6: {
    description: "Luật Xây dựng sửa đổi 2020 (Luật số 62/2020/QH14) sửa đổi, bổ sung một số điều của Luật Xây dựng 2014, nhằm tháo gỡ khó khăn và cải cách thủ tục hành chính trong quản lý đầu tư xây dựng.",
    chapters: [
      { title: "Phần 1: Sửa đổi điều khoản cơ bản", summary: "Điều chỉnh phạm vi áp dụng và các khái niệm về hoạt động xây dựng." },
      { title: "Phần 2: Lập, thẩm định dự án", summary: "Đơn giản hóa thủ tục lập, thẩm định dự án nhóm B và C." },
      { title: "Phần 3: Giấy phép xây dựng", summary: "Điều chỉnh điều kiện cấp phép, miễn phép xây dựng." },
      { title: "Phần 4: Điều khoản thi hành", summary: "Hiệu lực thi hành và điều khoản chuyển tiếp." },
    ],
    relatedIds: [4, 3, 1],
    keywords: ["giấy phép xây dựng", "thiết kế cơ sở", "chủ đầu tư", "công trình đặc biệt"],
  },
  7: {
    description: "Nghị định 40/2024/NĐ-CP quy định về đầu tư theo hình thức góp vốn, mua cổ phần, mua phần vốn góp của nhà đầu tư nước ngoài tại tổ chức kinh tế của Việt Nam.",
    chapters: [
      { title: "Chương I: Quy định chung", summary: "Điều kiện và nguyên tắc đầu tư nước ngoài vào doanh nghiệp Việt Nam." },
      { title: "Chương II: Góp vốn, mua cổ phần", summary: "Thủ tục đăng ký góp vốn, mua cổ phần của nhà đầu tư nước ngoài." },
      { title: "Chương III: Trường hợp đặc biệt", summary: "Quy định đối với ngành nghề kinh doanh có điều kiện với NĐT nước ngoài." },
    ],
    relatedIds: [2, 1, 8],
    keywords: ["nhà đầu tư nước ngoài", "góp vốn", "tỷ lệ sở hữu", "giấy chứng nhận đầu tư"],
  },
  8: {
    description: "Luật Ngân sách nhà nước 2015 quy định về lập, chấp hành, kiểm toán, quyết toán, giám sát ngân sách nhà nước; nhiệm vụ, quyền hạn của các cơ quan, tổ chức, đơn vị và cá nhân liên quan.",
    chapters: [
      { title: "Chương I: Quy định chung", summary: "Phạm vi ngân sách nhà nước, phân cấp ngân sách và năm ngân sách." },
      { title: "Chương II: Nhiệm vụ, quyền hạn các cấp", summary: "Thẩm quyền quyết định, lập, chấp hành ngân sách của Quốc hội, Chính phủ, UBND." },
      { title: "Chương III: Thu và chi ngân sách", summary: "Các khoản thu, chi ngân sách nhà nước và phân cấp nguồn thu." },
      { title: "Chương IV: Lập và quyết toán ngân sách", summary: "Quy trình lập dự toán, chấp hành và quyết toán ngân sách nhà nước hàng năm." },
    ],
    relatedIds: [5, 7, 1],
    keywords: ["ngân sách nhà nước", "thu ngân sách", "chi ngân sách", "dự toán", "quyết toán"],
  },
};

let KNOWLEDGE_TERMS: LegacyKnowledgeTerm[] = [];

let TREE_DATA: DocNode = {
  id: "root",
  label: "NĐ 15/2021/NĐ-CP",
  type: "root",
  summary: "Nghị định về quản lý dự án đầu tư xây dựng, áp dụng cho các dự án sử dụng vốn đầu tư công và vốn nhà nước ngoài đầu tư công trên toàn quốc.",
  children: [
    {
      id: "ch1", label: "Chương I\nQuy định chung", type: "chapter",
      summary: "Phạm vi điều chỉnh, đối tượng áp dụng và các khái niệm cơ bản trong quản lý dự án đầu tư xây dựng.",
      children: [
        { id: "a1", label: "Điều 1", type: "article", summary: "Phạm vi điều chỉnh — bao gồm tất cả dự án sử dụng vốn đầu tư công và vốn nhà nước ngoài đầu tư công." },
        { id: "a2", label: "Điều 2", type: "article", summary: "Đối tượng áp dụng: cơ quan nhà nước, tổ chức và cá nhân tham gia quản lý và thực hiện dự án." },
        { id: "a3", label: "Điều 3", type: "article", summary: "Giải thích từ ngữ: chủ đầu tư, ban quản lý dự án, nhà thầu tư vấn và các bên liên quan." },
      ],
    },
    {
      id: "ch2", label: "Chương II\nPhân loại dự án", type: "chapter",
      summary: "Quy định về thẩm quyền quyết định đầu tư và phân loại dự án theo quy mô, tính chất, nguồn vốn.",
      children: [
        { id: "a4", label: "Điều 4", type: "article", summary: "Phân loại dự án nhóm A, B, C theo tổng mức đầu tư và tính chất công trình." },
        { id: "a5", label: "Điều 5", type: "article", summary: "Thẩm quyền quyết định chủ trương đầu tư và phê duyệt báo cáo nghiên cứu khả thi." },
        { id: "a6", label: "Điều 6", type: "article", summary: "Trình tự, thủ tục phê duyệt dự án và các hồ sơ tài liệu cần thiết kèm theo." },
        { id: "a7", label: "Điều 7", type: "article", summary: "Điều chỉnh dự án: các trường hợp và thủ tục điều chỉnh tổng mức đầu tư trong quá trình thực hiện." },
      ],
    },
    {
      id: "ch3", label: "Chương III\nThực hiện dự án", type: "chapter",
      summary: "Quản lý thực hiện dự án, giám sát thi công, nghiệm thu và bàn giao công trình đưa vào khai thác sử dụng.",
      children: [
        { id: "a8", label: "Điều 8", type: "article", summary: "Hình thức quản lý dự án: ban QLDA chuyên ngành, khu vực hoặc thuê tư vấn quản lý." },
        { id: "a9", label: "Điều 9", type: "article", summary: "Giám sát thi công xây dựng và đảm bảo chất lượng, an toàn lao động tại công trường." },
        { id: "a10", label: "Điều 10", type: "article", summary: "Nghiệm thu, bàn giao và quyết toán công trình hoàn thành đưa vào khai thác sử dụng." },
      ],
    },
  ],
};

const SUMMARY_TABS = [
  { key: "context", label: "Bối cảnh", content: "Nghị định 15/2021/NĐ-CP được ban hành thay thế Nghị định 59/2015/NĐ-CP, đáp ứng yêu cầu quản lý dự án đầu tư xây dựng trong giai đoạn mới. Bối cảnh ban hành xuất phát từ sự gia tăng đáng kể số lượng và quy mô các dự án đầu tư công, cùng với nhu cầu hoàn thiện cơ chế quản lý nhà nước về xây dựng." },
  { key: "goal", label: "Mục tiêu", content: "Nghị định hướng đến mục tiêu nâng cao hiệu quả quản lý nhà nước về đầu tư xây dựng, phân định rõ trách nhiệm các bên tham gia, giảm thiểu thất thoát lãng phí ngân sách nhà nước và tăng cường minh bạch trong công tác đấu thầu, thi công và nghiệm thu công trình." },
  { key: "content", label: "Nội dung chính", content: "Nghị định gồm 3 chương, 10 điều quy định về: phân loại dự án theo nhóm A, B, C; thẩm quyền phê duyệt dự án; các hình thức ban quản lý dự án; quy trình giám sát, nghiệm thu; và quy định về điều chỉnh tổng mức đầu tư trong quá trình thực hiện." },
  { key: "decision", label: "Quyết định cần thiết", content: "Các cơ quan cần quyết định: (1) Lựa chọn hình thức ban QLDA phù hợp với quy mô dự án; (2) Bố trí kinh phí cho công tác chuẩn bị đầu tư; (3) Phê duyệt thiết kế kỹ thuật và dự toán trước khi triển khai. Cần làm rõ thẩm quyền phê duyệt đối với dự án nhóm B." },
  { key: "impact", label: "Tác động", content: "Tác động tích cực: rút ngắn thủ tục hành chính 30–40%, tăng cường phân cấp cho địa phương. Cần lưu ý: các địa phương cần nâng cao năng lực cán bộ; doanh nghiệp xây dựng cần cập nhật quy trình nội bộ phù hợp quy định mới trong năm 2025." },
];

const INIT_CHAT = [{ role: "assistant", text: "Xin chào! Tôi là trợ lý AI phân tích tài liệu. Hãy đặt câu hỏi về nội dung tài liệu NĐ 15/2021/NĐ-CP." }];
let ACTIVE_DOCUMENT_ID: string | null = null;

const HIGHLIGHT_TERMS = [
  { term: "vốn đầu tư công", definition: "Nguồn vốn thuộc ngân sách nhà nước, vốn từ nguồn thu hợp pháp của các cơ quan nhà nước dùng để đầu tư.", sectionId: "dieu-1" },
  { term: "nhà thầu", definition: "Tổ chức, cá nhân có năng lực, kinh nghiệm cung cấp dịch vụ tư vấn, thực hiện gói thầu xây lắp hoặc cung cấp hàng hóa theo hợp đồng.", sectionId: "dieu-2" },
  { term: "chủ đầu tư", definition: "Cơ quan, tổ chức được giao thực hiện dự án đầu tư xây dựng, bao gồm quản lý và sử dụng vốn để thực hiện hoạt động đầu tư.", sectionId: "dieu-3" },
  { term: "tổng mức đầu tư", definition: "Toàn bộ chi phí cần thiết để thực hiện dự án, được xác định trong giai đoạn lập dự án đầu tư xây dựng.", sectionId: "dieu-4" },
  { term: "dự án nhóm A", definition: "Dự án đầu tư xây dựng có tổng mức đầu tư từ 2.300 tỷ đồng trở lên, thuộc thẩm quyền phê duyệt của Thủ tướng Chính phủ.", sectionId: "dieu-4" },
  { term: "ban quản lý dự án", definition: "Tổ chức được thành lập để quản lý việc thực hiện các dự án đầu tư xây dựng sử dụng vốn nhà nước theo quy định.", sectionId: "dieu-8" },
  { term: "nghiệm thu", definition: "Quá trình kiểm tra, đánh giá và xác nhận khối lượng, chất lượng công việc xây dựng đã thực hiện theo hợp đồng và thiết kế.", sectionId: "dieu-10" },
];

const DOCUMENT_SECTIONS = [
  { id: "preamble", heading: "", content: "CHÍNH PHỦ ————— Số: 15/2021/NĐ-CP\n\nNGHỊ ĐỊNH\nQuy định về quản lý dự án đầu tư xây dựng\n\nCăn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015; Căn cứ Luật Xây dựng số 50/2014/QH13 ngày 18 tháng 6 năm 2014 và Luật số 62/2020/QH14 sửa đổi, bổ sung; Căn cứ Luật Đầu tư công số 39/2019/QH14 ngày 13 tháng 6 năm 2019; Theo đề nghị của Bộ trưởng Bộ Xây dựng; Chính phủ ban hành Nghị định quy định về quản lý dự án đầu tư xây dựng." },
  { id: "chuong-1", heading: "CHƯƠNG I — QUY ĐỊNH CHUNG", content: "" },
  { id: "dieu-1", heading: "Điều 1. Phạm vi điều chỉnh", content: "Nghị định này quy định về quản lý dự án đầu tư xây dựng sử dụng vốn đầu tư công, vốn nhà nước ngoài đầu tư công, bao gồm: lập, thẩm định, phê duyệt dự án đầu tư xây dựng; thực hiện dự án đầu tư xây dựng (gồm thiết kế, dự toán xây dựng; cấp phép xây dựng; lựa chọn nhà thầu; thi công xây dựng); nghiệm thu, bàn giao, đưa công trình vào khai thác sử dụng và các hoạt động khác có liên quan đến quản lý dự án đầu tư xây dựng." },
  { id: "dieu-2", heading: "Điều 2. Đối tượng áp dụng", content: "Nghị định này áp dụng đối với cơ quan, tổ chức, cá nhân tham gia hoạt động quản lý dự án đầu tư xây dựng sử dụng vốn đầu tư công, vốn nhà nước ngoài đầu tư công bao gồm: chủ đầu tư, ban quản lý dự án, nhà thầu tư vấn, nhà thầu xây dựng, nhà thầu cung cấp thiết bị và các tổ chức, cá nhân có liên quan. Nghị định này không áp dụng đối với dự án đầu tư xây dựng sử dụng vốn tư nhân, trừ trường hợp pháp luật có quy định khác." },
  { id: "dieu-3", heading: "Điều 3. Giải thích từ ngữ", content: "Trong Nghị định này, các từ ngữ dưới đây được hiểu như sau:\n1. Chủ đầu tư là cơ quan, tổ chức được giao thực hiện dự án đầu tư xây dựng sử dụng vốn đầu tư công, vốn nhà nước ngoài đầu tư công.\n2. Ban quản lý dự án là tổ chức được thành lập theo quyết định của cơ quan có thẩm quyền để thực hiện chức năng quản lý dự án đầu tư xây dựng.\n3. Nhà thầu là tổ chức, cá nhân có năng lực, kinh nghiệm cung cấp dịch vụ tư vấn, thực hiện gói thầu xây lắp hoặc cung cấp hàng hóa cho dự án." },
  { id: "chuong-2", heading: "CHƯƠNG II — PHÂN LOẠI DỰ ÁN VÀ THẨM QUYỀN QUYẾT ĐỊNH ĐẦU TƯ", content: "" },
  { id: "dieu-4", heading: "Điều 4. Phân loại dự án đầu tư xây dựng", content: "Dự án đầu tư xây dựng được phân loại theo quy mô, tính chất và nguồn vốn đầu tư như sau:\n1. Dự án nhóm A: là dự án có tổng mức đầu tư từ 2.300 tỷ đồng trở lên hoặc dự án thuộc các lĩnh vực đặc biệt quan trọng theo quyết định của Thủ tướng Chính phủ.\n2. Dự án nhóm B: là dự án có tổng mức đầu tư từ 120 tỷ đồng đến dưới 2.300 tỷ đồng.\n3. Dự án nhóm C: là dự án có tổng mức đầu tư dưới 120 tỷ đồng." },
  { id: "dieu-5", heading: "Điều 5. Thẩm quyền quyết định chủ trương đầu tư", content: "Thẩm quyền quyết định chủ trương đầu tư được phân cấp như sau:\n1. Quốc hội quyết định chủ trương đầu tư các chương trình, dự án quan trọng quốc gia.\n2. Thủ tướng Chính phủ quyết định chủ trương đầu tư dự án nhóm A sử dụng vốn đầu tư công.\n3. Bộ trưởng, Chủ tịch UBND cấp tỉnh quyết định chủ trương đầu tư dự án nhóm B và C do cơ quan mình quản lý." },
  { id: "dieu-6", heading: "Điều 6. Trình tự, thủ tục phê duyệt dự án", content: "Trình tự phê duyệt dự án đầu tư xây dựng bao gồm các bước: lập báo cáo nghiên cứu tiền khả thi (đối với dự án nhóm A), lập báo cáo nghiên cứu khả thi, tổ chức thẩm định, và phê duyệt dự án. Hồ sơ phê duyệt dự án bao gồm: tờ trình phê duyệt, báo cáo nghiên cứu khả thi, biên bản thẩm định và các tài liệu liên quan." },
  { id: "dieu-7", heading: "Điều 7. Điều chỉnh dự án đầu tư xây dựng", content: "Dự án đầu tư xây dựng được điều chỉnh trong các trường hợp: (1) Do tác động bất khả kháng làm thay đổi mục tiêu, quy mô đầu tư đã được phê duyệt; (2) Do quy hoạch điều chỉnh ảnh hưởng trực tiếp đến dự án; (3) Do thay đổi về cơ chế, chính sách của nhà nước. Khi điều chỉnh tổng mức đầu tư vượt quá 10%, chủ đầu tư phải báo cáo người quyết định đầu tư xem xét, quyết định." },
  { id: "chuong-3", heading: "CHƯƠNG III — THỰC HIỆN DỰ ÁN ĐẦU TƯ XÂY DỰNG", content: "" },
  { id: "dieu-8", heading: "Điều 8. Hình thức quản lý dự án", content: "Ban quản lý dự án được thành lập theo một trong ba hình thức: (1) Ban quản lý dự án chuyên ngành do Bộ, ngành thành lập để quản lý các dự án thuộc lĩnh vực chuyên ngành; (2) Ban quản lý dự án khu vực do UBND cấp tỉnh thành lập; (3) Chủ đầu tư thuê tổ chức tư vấn quản lý dự án có đủ điều kiện năng lực theo quy định. Chủ đầu tư có trách nhiệm giám sát, kiểm tra hoạt động của ban quản lý dự án hoặc tổ chức tư vấn được thuê." },
  { id: "dieu-9", heading: "Điều 9. Giám sát thi công xây dựng", content: "Chủ đầu tư phải tổ chức giám sát thi công xây dựng công trình trong suốt quá trình thi công. Nhà thầu giám sát phải có đủ điều kiện năng lực theo quy định, thực hiện giám sát chất lượng, khối lượng, tiến độ và an toàn lao động. Kết quả giám sát được lập thành nhật ký thi công và báo cáo định kỳ gửi chủ đầu tư." },
  { id: "dieu-10", heading: "Điều 10. Nghiệm thu và bàn giao công trình", content: "Nghiệm thu công trình xây dựng được thực hiện theo các bước: nghiệm thu từng công việc, nghiệm thu giai đoạn thi công, nghiệm thu hoàn thành hạng mục công trình và nghiệm thu hoàn thành toàn bộ công trình. Sau khi hoàn thành nghiệm thu, chủ đầu tư tổ chức bàn giao công trình cho đơn vị quản lý, vận hành khai thác theo quyết định của cơ quan có thẩm quyền." },
];

const LAW_FULL_TEXT: Record<number, { id: string; heading: string; content: string }[]> = {
  1: [
    { id: "p0", heading: "", content: "QUỐC HỘI ————— Luật số: 91/2015/QH13\n\nBỘ LUẬT DÂN SỰ\n\nCăn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam; Quốc hội ban hành Bộ luật dân sự." },
    { id: "p1", heading: "PHẦN THỨ NHẤT — QUY ĐỊNH CHUNG", content: "" },
    { id: "p1c1", heading: "Chương I. Những quy định chung", content: "" },
    { id: "p1d1", heading: "Điều 1. Phạm vi điều chỉnh", content: "Bộ luật này quy định địa vị pháp lý, chuẩn mực pháp lý về cách ứng xử của cá nhân, pháp nhân; quyền, nghĩa vụ về nhân thân và tài sản của cá nhân, pháp nhân trong các quan hệ dân sự được hình thành trên cơ sở bình đẳng, tự do ý chí, độc lập về tài sản và tự chịu trách nhiệm." },
    { id: "p1d2", heading: "Điều 2. Công nhận, tôn trọng, bảo vệ và bảo đảm quyền dân sự", content: "1. Ở nước Cộng hòa xã hội chủ nghĩa Việt Nam, các quyền dân sự được công nhận, tôn trọng, bảo vệ và bảo đảm theo Hiến pháp và pháp luật.\n2. Quyền dân sự chỉ có thể bị hạn chế theo quy định của luật trong trường hợp cần thiết vì lý do quốc phòng, an ninh quốc gia, trật tự, an toàn xã hội, đạo đức xã hội, sức khỏe của cộng đồng." },
    { id: "p1d3", heading: "Điều 3. Các nguyên tắc cơ bản của pháp luật dân sự", content: "1. Mọi cá nhân, pháp nhân đều bình đẳng, không được lấy bất kỳ lý do nào để phân biệt đối xử; được pháp luật bảo hộ như nhau về các quyền nhân thân và tài sản.\n2. Cá nhân, pháp nhân xác lập, thực hiện, chấm dứt quyền, nghĩa vụ dân sự của mình trên cơ sở tự do, tự nguyện cam kết, thỏa thuận. Mọi cam kết, thỏa thuận không vi phạm điều cấm của luật, không trái đạo đức xã hội có hiệu lực thực hiện đối với các bên và phải được chủ thể khác tôn trọng.\n3. Cá nhân, pháp nhân phải xác lập, thực hiện, chấm dứt quyền, nghĩa vụ dân sự của mình một cách thiện chí, trung thực." },
    { id: "p1d4", heading: "Điều 4. Áp dụng Bộ luật dân sự", content: "Bộ luật này là luật chung điều chỉnh các quan hệ dân sự. Luật khác có liên quan điều chỉnh quan hệ dân sự trong các lĩnh vực cụ thể không được trái với các nguyên tắc cơ bản của pháp luật dân sự quy định tại Điều 3 của Bộ luật này." },
    { id: "p2", heading: "PHẦN THỨ HAI — PHÁP NHÂN", content: "" },
    { id: "p2d74", heading: "Điều 74. Khái niệm pháp nhân", content: "Một tổ chức được công nhận là pháp nhân khi có đủ các điều kiện sau đây:\n1. Được thành lập theo quy định của Bộ luật này, luật khác có liên quan;\n2. Có cơ cấu tổ chức theo quy định tại Điều 83 của Bộ luật này;\n3. Có tài sản độc lập với cá nhân, pháp nhân khác và tự chịu trách nhiệm bằng tài sản của mình;\n4. Nhân danh mình tham gia quan hệ pháp luật một cách độc lập." },
    { id: "p2d75", heading: "Điều 75. Phân loại pháp nhân", content: "Pháp nhân thương mại là pháp nhân có mục tiêu chính là tìm kiếm lợi nhuận và lợi nhuận được chia cho các thành viên. Pháp nhân phi thương mại là pháp nhân không có mục tiêu chính là tìm kiếm lợi nhuận; nếu có lợi nhuận thì cũng không được phân chia cho các thành viên." },
    { id: "p3", heading: "PHẦN THỨ BA — TÀI SẢN VÀ QUYỀN SỞ HỮU", content: "" },
    { id: "p3d105", heading: "Điều 105. Tài sản", content: "1. Tài sản là vật, tiền, giấy tờ có giá và quyền tài sản.\n2. Tài sản bao gồm bất động sản và động sản. Bất động sản và động sản có thể là tài sản hiện có và tài sản hình thành trong tương lai." },
    { id: "p3d158", heading: "Điều 158. Quyền sở hữu", content: "Quyền sở hữu bao gồm quyền chiếm hữu, quyền sử dụng và quyền định đoạt tài sản của chủ sở hữu theo quy định của luật." },
    { id: "p4", heading: "PHẦN THỨ TƯ — NGHĨA VỤ VÀ HỢP ĐỒNG", content: "" },
    { id: "p4d274", heading: "Điều 274. Khái niệm nghĩa vụ", content: "Nghĩa vụ là việc mà theo đó, một hoặc nhiều chủ thể (sau đây gọi chung là bên có nghĩa vụ) phải chuyển giao vật, chuyển giao quyền, trả tiền hoặc giấy tờ có giá, thực hiện công việc hoặc không được thực hiện công việc nhất định vì lợi ích của một hoặc nhiều chủ thể khác (sau đây gọi chung là bên có quyền)." },
    { id: "p4d385", heading: "Điều 385. Khái niệm hợp đồng", content: "Hợp đồng là sự thỏa thuận giữa các bên về việc xác lập, thay đổi hoặc chấm dứt quyền, nghĩa vụ dân sự." },
    { id: "p5", heading: "PHẦN THỨ NĂM — THỪA KẾ", content: "" },
    { id: "p5d609", heading: "Điều 609. Quyền thừa kế", content: "Cá nhân có quyền lập di chúc để định đoạt tài sản của mình; để lại tài sản của mình cho người thừa kế theo pháp luật; hưởng di sản theo di chúc hoặc theo pháp luật. Người thừa kế không là cá nhân có quyền hưởng di sản theo di chúc." },
    { id: "p6", heading: "PHẦN THỨ SÁU — QUAN HỆ DÂN SỰ CÓ YẾU TỐ NƯỚC NGOÀI", content: "" },
    { id: "p6d663", heading: "Điều 663. Phạm vi áp dụng", content: "Phần này quy định pháp luật áp dụng đối với quan hệ dân sự có yếu tố nước ngoài. Trường hợp luật khác có quy định về pháp luật áp dụng đối với quan hệ dân sự có yếu tố nước ngoài thì áp dụng theo quy định của luật đó." },
    { id: "end", heading: "ĐIỀU KHOẢN THI HÀNH", content: "Bộ luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2017. Bộ luật dân sự số 33/2005/QH11 hết hiệu lực kể từ ngày Bộ luật này có hiệu lực thi hành.\n\nLuật này đã được Quốc hội nước Cộng hòa xã hội chủ nghĩa Việt Nam khóa XIII, kỳ họp thứ 10 thông qua ngày 24 tháng 11 năm 2015.\n\nCHỦ TỊCH QUỐC HỘI\nNguyễn Sinh Hùng" },
  ],
  2: [
    { id: "p0", heading: "", content: "QUỐC HỘI ————— Luật số: 59/2020/QH14\n\nLUẬT DOANH NGHIỆP\n\nCăn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam; Quốc hội ban hành Luật Doanh nghiệp." },
    { id: "c1", heading: "CHƯƠNG I — QUY ĐỊNH CHUNG", content: "" },
    { id: "d1", heading: "Điều 1. Phạm vi điều chỉnh", content: "Luật này quy định về việc thành lập, tổ chức quản lý, tổ chức lại, giải thể và hoạt động có liên quan của doanh nghiệp, bao gồm công ty trách nhiệm hữu hạn, công ty cổ phần, công ty hợp danh và doanh nghiệp tư nhân; quy định về nhóm công ty." },
    { id: "d4", heading: "Điều 4. Giải thích từ ngữ", content: "Trong Luật này, các từ ngữ dưới đây được hiểu như sau:\n1. Cổ đông là cá nhân hoặc tổ chức sở hữu ít nhất một cổ phần của công ty cổ phần.\n2. Cổ đông sáng lập là cổ đông sở hữu ít nhất một cổ phần phổ thông và ký tên trong danh sách cổ đông sáng lập công ty cổ phần.\n3. Công ty là tổ chức kinh tế có tư cách pháp nhân được thành lập và đăng ký kinh doanh theo quy định của pháp luật.\n4. Vốn điều lệ là tổng giá trị tài sản do các thành viên công ty, chủ sở hữu công ty đã góp hoặc cam kết góp khi thành lập công ty trách nhiệm hữu hạn, công ty hợp danh; là tổng mệnh giá cổ phần đã bán hoặc được đăng ký mua khi thành lập công ty cổ phần." },
    { id: "c2", heading: "CHƯƠNG II — THÀNH LẬP DOANH NGHIỆP VÀ ĐĂNG KÝ KINH DOANH", content: "" },
    { id: "d17", heading: "Điều 17. Quyền thành lập, góp vốn, mua cổ phần, mua phần vốn góp và quản lý doanh nghiệp", content: "1. Tổ chức, cá nhân có quyền thành lập và quản lý doanh nghiệp tại Việt Nam theo quy định của Luật này, trừ trường hợp quy định tại khoản 2 Điều này.\n2. Tổ chức, cá nhân sau đây không có quyền thành lập và quản lý doanh nghiệp tại Việt Nam:\na) Cơ quan nhà nước, đơn vị lực lượng vũ trang nhân dân sử dụng tài sản nhà nước để thành lập doanh nghiệp kinh doanh thu lợi riêng cho cơ quan, đơn vị mình;\nb) Cán bộ, công chức, viên chức theo quy định của Luật Cán bộ, công chức và Luật Viên chức." },
    { id: "d26", heading: "Điều 26. Hồ sơ đăng ký doanh nghiệp", content: "Hồ sơ đăng ký doanh nghiệp bao gồm:\n1. Giấy đề nghị đăng ký doanh nghiệp;\n2. Điều lệ công ty;\n3. Danh sách thành viên hoặc danh sách cổ đông sáng lập;\n4. Bản sao giấy tờ pháp lý của cá nhân đối với người đại diện theo pháp luật và thành viên, cổ đông sáng lập;\n5. Văn bản xác nhận vốn pháp định nếu pháp luật có quy định." },
    { id: "c3", heading: "CHƯƠNG III — CÔNG TY TRÁCH NHIỆM HỮU HẠN", content: "" },
    { id: "d46", heading: "Điều 46. Công ty trách nhiệm hữu hạn hai thành viên trở lên", content: "1. Công ty trách nhiệm hữu hạn hai thành viên trở lên là doanh nghiệp có từ 02 đến 50 thành viên là tổ chức, cá nhân. Thành viên chịu trách nhiệm về các khoản nợ và nghĩa vụ tài sản khác của doanh nghiệp trong phạm vi số vốn đã góp vào doanh nghiệp, trừ trường hợp quy định tại khoản 4 Điều 47 của Luật này.\n2. Phần vốn góp của thành viên chỉ được chuyển nhượng theo quy định tại các Điều 51, 52 và 53 của Luật này." },
    { id: "c4", heading: "CHƯƠNG IV — CÔNG TY CỔ PHẦN", content: "" },
    { id: "d111", heading: "Điều 111. Công ty cổ phần", content: "1. Công ty cổ phần là doanh nghiệp, trong đó:\na) Vốn điều lệ được chia thành nhiều phần bằng nhau gọi là cổ phần;\nb) Cổ đông có thể là tổ chức, cá nhân; số lượng cổ đông tối thiểu là 03 và không hạn chế số lượng tối đa;\nc) Cổ đông chỉ chịu trách nhiệm về các khoản nợ và nghĩa vụ tài sản khác của doanh nghiệp trong phạm vi số vốn đã góp vào doanh nghiệp;\nd) Cổ đông có quyền tự do chuyển nhượng cổ phần của mình cho người khác, trừ trường hợp quy định tại khoản 3 Điều 120 và khoản 1 Điều 127 của Luật này." },
    { id: "c5", heading: "CHƯƠNG V — TỔ CHỨC LẠI DOANH NGHIỆP", content: "" },
    { id: "d200", heading: "Điều 200. Chia doanh nghiệp", content: "Công ty trách nhiệm hữu hạn, công ty cổ phần có thể chia các tài sản, quyền và nghĩa vụ, thành viên, cổ đông của công ty hiện có (sau đây gọi là công ty bị chia) để thành lập hai hoặc nhiều công ty mới." },
    { id: "end", heading: "ĐIỀU KHOẢN THI HÀNH", content: "Luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2021.\nLuật Doanh nghiệp số 68/2014/QH13 hết hiệu lực kể từ ngày Luật này có hiệu lực thi hành.\n\nCHỦ TỊCH QUỐC HỘI\nNguyễn Thị Kim Ngân" },
  ],
  3: [
    { id: "p0", heading: "", content: "QUỐC HỘI ————— Luật số: 22/2023/QH15\n\nLUẬT ĐẤU THẦU\n\nCăn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam; Quốc hội ban hành Luật Đấu thầu." },
    { id: "c1", heading: "CHƯƠNG I — QUY ĐỊNH CHUNG", content: "" },
    { id: "d1", heading: "Điều 1. Phạm vi điều chỉnh", content: "Luật này quy định quản lý nhà nước về đấu thầu; trách nhiệm của các bên trong hoạt động đấu thầu; lựa chọn nhà thầu thực hiện gói thầu, lựa chọn nhà đầu tư thực hiện dự án đầu tư kinh doanh; giải quyết kiến nghị và xử lý vi phạm trong đấu thầu." },
    { id: "d4", heading: "Điều 4. Giải thích từ ngữ", content: "Trong Luật này, các từ ngữ dưới đây được hiểu như sau:\n1. Đấu thầu là quá trình lựa chọn nhà thầu để ký kết và thực hiện hợp đồng cung cấp dịch vụ tư vấn, dịch vụ phi tư vấn, mua sắm hàng hóa, xây lắp; lựa chọn nhà đầu tư để ký kết và thực hiện hợp đồng dự án đầu tư kinh doanh trên cơ sở đảm bảo cạnh tranh, công bằng, minh bạch và hiệu quả kinh tế.\n2. Nhà thầu là tổ chức, cá nhân có năng lực, kinh nghiệm tham dự thầu cung cấp dịch vụ tư vấn, dịch vụ phi tư vấn, hàng hóa, xây lắp.\n3. Hồ sơ mời thầu (HSMT) là toàn bộ tài liệu sử dụng cho hình thức đấu thầu rộng rãi, đấu thầu hạn chế, bao gồm các yêu cầu cho một gói thầu, làm căn cứ để nhà thầu, nhà đầu tư chuẩn bị hồ sơ dự thầu và là căn cứ để bên mời thầu đánh giá hồ sơ dự thầu." },
    { id: "d10", heading: "Điều 10. Các hành vi bị cấm trong đấu thầu", content: "1. Đưa, nhận, môi giới hối lộ trong đấu thầu.\n2. Gian lận trong đấu thầu.\n3. Cản trở hoạt động đấu thầu.\n4. Thông thầu.\n5. Chuyển nhượng thầu trái quy định của pháp luật.\n6. Vi phạm quy định của pháp luật về bảo đảm cạnh tranh trong đấu thầu.\n7. Tiết lộ, tiếp cận các tài liệu đấu thầu của gói thầu trái quy định của pháp luật." },
    { id: "c2", heading: "CHƯƠNG II — KẾ HOẠCH LỰA CHỌN NHÀ THẦU", content: "" },
    { id: "d35", heading: "Điều 35. Lập kế hoạch lựa chọn nhà thầu", content: "Kế hoạch lựa chọn nhà thầu được lập cho toàn bộ dự án, dự toán mua sắm. Trường hợp chưa đủ điều kiện lập kế hoạch lựa chọn nhà thầu cho toàn bộ dự án thì lập kế hoạch lựa chọn nhà thầu cho một hoặc một số gói thầu để thực hiện trước." },
    { id: "c3", heading: "CHƯƠNG III — HÌNH THỨC VÀ PHƯƠNG THỨC LỰA CHỌN NHÀ THẦU", content: "" },
    { id: "d20", heading: "Điều 20. Đấu thầu rộng rãi", content: "Đấu thầu rộng rãi là hình thức lựa chọn nhà thầu trong đó không hạn chế số lượng nhà thầu tham dự. Đấu thầu rộng rãi được áp dụng cho tất cả các gói thầu, trừ trường hợp quy định tại các điều 21, 22, 23, 24 và 25 của Luật này." },
    { id: "d22", heading: "Điều 22. Chỉ định thầu", content: "Chỉ định thầu được áp dụng trong các trường hợp sau đây:\n1. Gói thầu cần thực hiện để khắc phục ngay hoặc xử lý kịp thời hậu quả gây ra do sự cố bất khả kháng;\n2. Gói thầu cần triển khai ngay để tránh gây nguy hại trực tiếp đến tính mạng, sức khỏe và tài sản của cộng đồng;\n3. Gói thầu mua sắm nhằm duy trì hoạt động thường xuyên của cơ quan nhà nước khi xảy ra sự cố bất khả kháng.\n4. Gói thầu có giá trị trong hạn mức theo quy định của Chính phủ." },
    { id: "c4", heading: "CHƯƠNG IV — QUY TRÌNH LỰA CHỌN NHÀ THẦU", content: "" },
    { id: "d36", heading: "Điều 36. Chuẩn bị lựa chọn nhà thầu", content: "Chuẩn bị lựa chọn nhà thầu bao gồm: lựa chọn danh sách ngắn đối với đấu thầu hạn chế; chuẩn bị hồ sơ mời thầu hoặc hồ sơ yêu cầu; thẩm định và phê duyệt hồ sơ mời thầu hoặc hồ sơ yêu cầu." },
    { id: "c5", heading: "CHƯƠNG V — THỰC HIỆN HỢP ĐỒNG", content: "" },
    { id: "d64", heading: "Điều 64. Nguyên tắc thực hiện hợp đồng", content: "1. Hợp đồng phải được thực hiện trung thực, theo đúng cam kết và đúng quy định của pháp luật.\n2. Bên mời thầu và nhà thầu có nghĩa vụ hợp tác với nhau trong quá trình thực hiện hợp đồng để đảm bảo hợp đồng được thực hiện theo đúng tiến độ, chất lượng và các điều kiện đã cam kết." },
    { id: "end", heading: "ĐIỀU KHOẢN THI HÀNH", content: "Luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2024.\nLuật Đấu thầu số 43/2013/QH13 hết hiệu lực kể từ ngày Luật này có hiệu lực thi hành.\n\nCHỦ TỊCH QUỐC HỘI\nVương Đình Huệ" },
  ],
  4: [
    { id: "p0", heading: "", content: "CHÍNH PHỦ ————— Số: 24/2024/NĐ-CP\n\nNGHỊ ĐỊNH\nQuy định chi tiết một số điều và biện pháp thi hành Luật Xây dựng về quản lý dự án đầu tư xây dựng\n\nCăn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015; Căn cứ Luật Xây dựng số 50/2014/QH13 và Luật số 62/2020/QH14 sửa đổi, bổ sung; Theo đề nghị của Bộ trưởng Bộ Xây dựng; Chính phủ ban hành Nghị định quy định chi tiết một số điều và biện pháp thi hành Luật Xây dựng về quản lý dự án đầu tư xây dựng." },
    { id: "c1", heading: "CHƯƠNG I — QUY ĐỊNH CHUNG", content: "" },
    { id: "d1", heading: "Điều 1. Phạm vi điều chỉnh", content: "Nghị định này quy định chi tiết về quản lý dự án đầu tư xây dựng gồm: lập, thẩm định dự án đầu tư xây dựng; thiết kế xây dựng; thi công xây dựng; quản lý hợp đồng xây dựng; nghiệm thu, bàn giao và bảo hành công trình xây dựng." },
    { id: "d3", heading: "Điều 3. Giải thích từ ngữ", content: "1. Chủ đầu tư là cơ quan, tổ chức, cá nhân sở hữu vốn, vay vốn hoặc được giao trực tiếp quản lý, sử dụng vốn để thực hiện hoạt động đầu tư xây dựng.\n2. Tổng thầu là nhà thầu ký kết hợp đồng trực tiếp với chủ đầu tư để nhận thầu toàn bộ một hoặc nhiều loại công việc của dự án đầu tư xây dựng.\n3. Nhà thầu phụ là nhà thầu ký kết hợp đồng với tổng thầu hoặc nhà thầu chính để thực hiện một phần công việc của tổng thầu hoặc nhà thầu chính." },
    { id: "c2", heading: "CHƯƠNG II — LẬP VÀ THẨM ĐỊNH DỰ ÁN ĐẦU TƯ XÂY DỰNG", content: "" },
    { id: "d5", heading: "Điều 5. Lập dự án đầu tư xây dựng", content: "Dự án đầu tư xây dựng được lập nhằm xem xét, đánh giá hiệu quả về mặt kinh tế — xã hội, hiệu quả tài chính của dự án; làm cơ sở xem xét, quyết định đầu tư. Báo cáo nghiên cứu khả thi phải đáp ứng các yêu cầu: sự cần thiết phải đầu tư, mục tiêu xây dựng; địa điểm xây dựng, diện tích sử dụng đất; quy mô, công suất, công nghệ; phương án thiết kế kiến trúc; phương án giải phóng mặt bằng; tổng mức đầu tư xây dựng; nguồn vốn và tiến độ thực hiện." },
    { id: "c3", heading: "CHƯƠNG III — THIẾT KẾ XÂY DỰNG", content: "" },
    { id: "d12", heading: "Điều 12. Các bước thiết kế xây dựng", content: "Thiết kế xây dựng công trình được thực hiện theo các bước: thiết kế cơ sở (trong giai đoạn chuẩn bị dự án); thiết kế kỹ thuật hoặc thiết kế bản vẽ thi công (trong giai đoạn thực hiện dự án).\nĐối với công trình đơn giản, thiết kế một bước là thiết kế bản vẽ thi công.\nĐối với công trình có quy mô lớn, tính chất phức tạp, việc thiết kế được thực hiện theo 2 bước: thiết kế kỹ thuật và thiết kế bản vẽ thi công." },
    { id: "c4", heading: "CHƯƠNG IV — THI CÔNG XÂY DỰNG", content: "" },
    { id: "d18", heading: "Điều 18. Điều kiện khởi công xây dựng", content: "Công trình xây dựng chỉ được khởi công khi đáp ứng các điều kiện:\n1. Có mặt bằng xây dựng để bàn giao toàn bộ hoặc từng phần theo tiến độ xây dựng;\n2. Có giấy phép xây dựng đối với công trình theo quy định phải có giấy phép xây dựng;\n3. Có thiết kế bản vẽ thi công của hạng mục, công trình được phê duyệt;\n4. Có hợp đồng xây dựng giữa chủ đầu tư và nhà thầu xây dựng;\n5. Có biện pháp đảm bảo an toàn, vệ sinh môi trường trong quá trình thi công xây dựng." },
    { id: "d22", heading: "Điều 22. Nghiệm thu công trình xây dựng", content: "Nghiệm thu công trình xây dựng bao gồm:\n1. Nghiệm thu từng công việc xây dựng trong quá trình thi công;\n2. Nghiệm thu hoàn thành hạng mục công trình, công trình xây dựng để đưa vào sử dụng;\n3. Trước khi nghiệm thu, chủ đầu tư phải tổ chức kiểm tra công tác nghiệm thu của nhà thầu và lập biên bản nghiệm thu theo quy định." },
    { id: "end", heading: "ĐIỀU KHOẢN THI HÀNH", content: "Nghị định này có hiệu lực thi hành từ ngày 01 tháng 04 năm 2024.\n\nTM. CHÍNH PHỦ\nTHỦ TƯỚNG\nPhạm Minh Chính" },
  ],
  5: [
    { id: "p0", heading: "", content: "BỘ TÀI CHÍNH ————— Số: 03/2023/TT-BTC\n\nTHÔNG TƯ\nQuy định về chế độ kế toán áp dụng cho cơ quan thuế\n\nCăn cứ Luật Kế toán số 88/2015/QH13; Căn cứ Nghị định số 174/2016/NĐ-CP quy định chi tiết một số điều của Luật Kế toán; Theo đề nghị của Cục trưởng Cục Quản lý, giám sát kế toán, kiểm toán; Bộ trưởng Bộ Tài chính ban hành Thông tư quy định về chế độ kế toán áp dụng cho cơ quan thuế.\n\n⚠ LƯU Ý: Thông tư này đã hết hiệu lực thi hành từ ngày 01/01/2025." },
    { id: "c1", heading: "CHƯƠNG I — QUY ĐỊNH CHUNG", content: "" },
    { id: "d1", heading: "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng", content: "Thông tư này quy định về chứng từ kế toán, tài khoản kế toán, sổ kế toán và báo cáo tài chính áp dụng đối với các cơ quan thuế các cấp (Tổng cục Thuế, Cục Thuế tỉnh, Chi cục Thuế quận huyện, Chi cục Thuế khu vực)." },
    { id: "d3", heading: "Điều 3. Nguyên tắc kế toán", content: "1. Đơn vị kế toán phải thu thập, phản ánh khách quan, đầy đủ, đúng thực tế và đúng kỳ kế toán mà nghiệp vụ kinh tế, tài chính phát sinh.\n2. Cơ sở dồn tích: tất cả các nghiệp vụ kinh tế, tài chính liên quan đến tài sản, nợ phải trả, nguồn vốn, doanh thu, chi phí phải được ghi sổ kế toán vào thời điểm phát sinh, không căn cứ vào thời điểm thực tế thu hoặc thực tế chi tiền." },
    { id: "c2", heading: "CHƯƠNG II — TÀI KHOẢN KẾ TOÁN", content: "" },
    { id: "d5", heading: "Điều 5. Hệ thống tài khoản kế toán", content: "Hệ thống tài khoản kế toán áp dụng cho cơ quan thuế bao gồm các tài khoản thuộc các loại:\n- Loại 1: Tài sản ngắn hạn (TK 111 Tiền mặt, TK 112 Tiền gửi ngân hàng, TK 131 Phải thu từ thuế...)\n- Loại 3: Nợ phải trả (TK 331 Phải trả người bán, TK 333 Thuế phải nộp nhà nước...)\n- Loại 5: Doanh thu thuế (TK 511 Doanh thu thu thuế nội địa...)\n- Loại 6: Chi phí (TK 611 Chi phí hoạt động...)" },
    { id: "c3", heading: "CHƯƠNG III — BÁO CÁO TÀI CHÍNH", content: "" },
    { id: "d8", heading: "Điều 8. Báo cáo tài chính định kỳ", content: "Cơ quan thuế phải lập và nộp báo cáo tài chính định kỳ như sau:\n1. Báo cáo quý: lập và nộp trong vòng 15 ngày kể từ ngày kết thúc quý;\n2. Báo cáo năm: lập và nộp trong vòng 30 ngày kể từ ngày 31/12.\nBáo cáo tài chính bao gồm: Bảng cân đối kế toán; Báo cáo kết quả thu ngân sách; Thuyết minh báo cáo tài chính." },
    { id: "end", heading: "ĐIỀU KHOẢN THI HÀNH", content: "Thông tư này có hiệu lực thi hành từ ngày 01 tháng 4 năm 2023 và hết hiệu lực từ ngày 01 tháng 01 năm 2025.\n\nKT. BỘ TRƯỞNG\nTHỨ TRƯỞNG\nCao Anh Tuấn" },
  ],
  6: [
    { id: "p0", heading: "", content: "QUỐC HỘI ————— Luật số: 62/2020/QH14\n\nLUẬT SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA LUẬT XÂY DỰNG\n\nCăn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam; Quốc hội ban hành Luật sửa đổi, bổ sung một số điều của Luật Xây dựng số 50/2014/QH13." },
    { id: "d1", heading: "Điều 1. Sửa đổi, bổ sung một số điều của Luật Xây dựng", content: "Sửa đổi, bổ sung một số điều của Luật Xây dựng số 50/2014/QH13 như sau:\n\n1. Sửa đổi, bổ sung khoản 10 Điều 3 về giải thích từ ngữ:\n\"Giấy phép xây dựng là văn bản pháp lý do cơ quan nhà nước có thẩm quyền cấp cho chủ đầu tư để xây dựng mới, sửa chữa, cải tạo, di dời công trình.\"\n\n2. Bổ sung điểm đ vào khoản 2 Điều 89 về các công trình được miễn phép xây dựng:\n\"đ) Công trình hạ tầng kỹ thuật viễn thông thụ động theo quy hoạch được cấp có thẩm quyền phê duyệt.\"" },
    { id: "s1", heading: "Phần 1 — Sửa đổi điều khoản về quản lý dự án", content: "Luật sửa đổi điều chỉnh thẩm quyền thẩm định dự án đầu tư xây dựng, theo đó:\n- Đơn giản hóa thủ tục thẩm định đối với dự án nhóm B và C sử dụng vốn ngân sách nhà nước;\n- Phân cấp thẩm quyền cho địa phương đối với dự án trên địa bàn tỉnh;\n- Rút ngắn thời gian thẩm định từ 45 ngày xuống còn 30 ngày đối với dự án nhóm C." },
    { id: "s2", heading: "Phần 2 — Sửa đổi về cấp phép xây dựng", content: "Luật sửa đổi bổ sung các trường hợp miễn cấp phép xây dựng, cụ thể:\n- Công trình xây dựng cấp IV ở địa bàn nông thôn;\n- Công trình xây dựng có quy mô dưới 07 tầng và diện tích dưới 500m² tại khu vực không có quy hoạch;\n- Công trình phục vụ quốc phòng, an ninh.\nĐồng thời, bãi bỏ quy định về gia hạn giấy phép xây dựng, thay bằng hình thức cấp lại." },
    { id: "s3", heading: "Phần 3 — Sửa đổi về thiết kế xây dựng", content: "Luật điều chỉnh yêu cầu về thẩm định thiết kế xây dựng:\n- Chủ đầu tư tự thẩm định thiết kế kỹ thuật đối với công trình cấp III, cấp IV;\n- Cơ quan chuyên môn về xây dựng thẩm định thiết kế kỹ thuật đối với công trình cấp đặc biệt, cấp I, cấp II;\n- Bỏ quy định bắt buộc thuê tổ chức tư vấn thẩm tra thiết kế đối với công trình nhóm C." },
    { id: "d2", heading: "Điều 2. Điều khoản thi hành", content: "1. Luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2021.\n2. Các dự án đầu tư xây dựng đã được quyết định đầu tư trước ngày Luật này có hiệu lực thi hành được tiếp tục thực hiện theo các quy định của pháp luật về xây dựng trước ngày Luật này có hiệu lực.\n3. Chính phủ, Bộ Xây dựng, các bộ, ngành và Ủy ban nhân dân các cấp trong phạm vi nhiệm vụ, quyền hạn của mình có trách nhiệm hướng dẫn thi hành Luật này." },
    { id: "end", heading: "KÝ BAN HÀNH", content: "Luật này đã được Quốc hội nước Cộng hòa xã hội chủ nghĩa Việt Nam khóa XIV, kỳ họp thứ 9 thông qua ngày 17 tháng 6 năm 2020.\n\nCHỦ TỊCH QUỐC HỘI\nNguyễn Thị Kim Ngân" },
  ],
  7: [
    { id: "p0", heading: "", content: "CHÍNH PHỦ ————— Số: 40/2024/NĐ-CP\n\nNGHỊ ĐỊNH\nQuy định về hoạt động đầu tư của nhà đầu tư nước ngoài và tổ chức kinh tế có vốn đầu tư nước ngoài\n\nCăn cứ Luật Đầu tư số 61/2020/QH14; Theo đề nghị của Bộ trưởng Bộ Kế hoạch và Đầu tư; Chính phủ ban hành Nghị định quy định về hoạt động đầu tư của nhà đầu tư nước ngoài." },
    { id: "c1", heading: "CHƯƠNG I — QUY ĐỊNH CHUNG", content: "" },
    { id: "d1", heading: "Điều 1. Phạm vi điều chỉnh", content: "Nghị định này quy định về điều kiện, thủ tục đầu tư theo hình thức góp vốn, mua cổ phần, mua phần vốn góp của nhà đầu tư nước ngoài vào tổ chức kinh tế tại Việt Nam; quyền và nghĩa vụ của nhà đầu tư nước ngoài khi thực hiện các hoạt động đầu tư tại Việt Nam." },
    { id: "d3", heading: "Điều 3. Nguyên tắc đầu tư nước ngoài", content: "1. Nhà đầu tư nước ngoài được áp dụng điều kiện đầu tư như nhà đầu tư trong nước trong trường hợp không có quy định khác tại điều ước quốc tế mà Việt Nam là thành viên.\n2. Nhà đầu tư nước ngoài khi góp vốn, mua cổ phần phải đáp ứng điều kiện về tỷ lệ sở hữu vốn điều lệ của tổ chức kinh tế theo quy định pháp luật về điều kiện đầu tư kinh doanh và điều ước quốc tế.\n3. Giấy chứng nhận đăng ký đầu tư là điều kiện bắt buộc trước khi nhà đầu tư nước ngoài thực hiện góp vốn lần đầu vào tổ chức kinh tế tại Việt Nam." },
    { id: "c2", heading: "CHƯƠNG II — GÓP VỐN, MUA CỔ PHẦN, MUA PHẦN VỐN GÓP", content: "" },
    { id: "d5", heading: "Điều 5. Điều kiện góp vốn, mua cổ phần, mua phần vốn góp", content: "Nhà đầu tư nước ngoài được góp vốn, mua cổ phần, mua phần vốn góp của tổ chức kinh tế nếu đáp ứng các điều kiện sau:\n1. Tỷ lệ sở hữu vốn điều lệ của nhà đầu tư nước ngoài không vượt mức quy định trong điều ước quốc tế mà Việt Nam là thành viên;\n2. Không thuộc ngành, nghề chưa tiếp cận thị trường đối với nhà đầu tư nước ngoài theo quy định của pháp luật;\n3. Đáp ứng điều kiện về hình thức đầu tư theo quy định của pháp luật có liên quan." },
    { id: "d8", heading: "Điều 8. Thủ tục đăng ký góp vốn, mua cổ phần", content: "Nhà đầu tư nước ngoài thực hiện thủ tục đăng ký góp vốn, mua cổ phần, mua phần vốn góp như sau:\n1. Nộp hồ sơ tại Sở Kế hoạch và Đầu tư nơi tổ chức kinh tế có trụ sở chính;\n2. Hồ sơ gồm: văn bản đăng ký góp vốn; bản sao giấy tờ pháp lý của nhà đầu tư; thỏa thuận nguyên tắc về góp vốn;\n3. Trong 15 ngày làm việc kể từ ngày nhận đủ hồ sơ hợp lệ, Sở Kế hoạch và Đầu tư có ý kiến bằng văn bản." },
    { id: "c3", heading: "CHƯƠNG III — TRƯỜNG HỢP ĐẶC BIỆT", content: "" },
    { id: "d12", heading: "Điều 12. Ngành nghề kinh doanh có điều kiện", content: "Nhà đầu tư nước ngoài đầu tư vào ngành nghề kinh doanh có điều kiện phải đáp ứng điều kiện theo quy định tại Luật Đầu tư và pháp luật chuyên ngành trước khi thực hiện đầu tư. Bộ, cơ quan ngang Bộ quản lý ngành có trách nhiệm kiểm tra điều kiện đầu tư kinh doanh đối với nhà đầu tư nước ngoài trong lĩnh vực thuộc phạm vi quản lý." },
    { id: "end", heading: "ĐIỀU KHOẢN THI HÀNH", content: "Nghị định này có hiệu lực thi hành từ ngày 01 tháng 05 năm 2024.\n\nTM. CHÍNH PHỦ\nTHỦ TƯỚNG\nPhạm Minh Chính" },
  ],
  8: [
    { id: "p0", heading: "", content: "QUỐC HỘI ————— Luật số: 83/2015/QH13\n\nLUẬT NGÂN SÁCH NHÀ NƯỚC\n\nCăn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam; Quốc hội ban hành Luật Ngân sách nhà nước." },
    { id: "c1", heading: "CHƯƠNG I — NHỮNG QUY ĐỊNH CHUNG", content: "" },
    { id: "d1", heading: "Điều 1. Phạm vi điều chỉnh", content: "Luật này quy định về lập, chấp hành, kiểm toán, quyết toán, giám sát ngân sách nhà nước; nhiệm vụ, quyền hạn của các cơ quan, tổ chức, đơn vị, cá nhân có liên quan trong lĩnh vực ngân sách nhà nước; quản lý, sử dụng ngân sách nhà nước." },
    { id: "d4", heading: "Điều 4. Giải thích từ ngữ", content: "1. Ngân sách nhà nước là toàn bộ các khoản thu, chi của Nhà nước được dự toán và thực hiện trong một khoảng thời gian nhất định do cơ quan nhà nước có thẩm quyền quyết định để bảo đảm thực hiện các chức năng, nhiệm vụ của Nhà nước.\n2. Thu ngân sách nhà nước bao gồm các khoản thuế, phí, lệ phí; các khoản thu từ hoạt động kinh tế của Nhà nước; các khoản đóng góp của các tổ chức và cá nhân; các khoản viện trợ; các khoản thu khác theo quy định của pháp luật.\n3. Chi ngân sách nhà nước bao gồm các khoản chi phát triển kinh tế — xã hội, bảo đảm quốc phòng, an ninh, bảo đảm hoạt động của bộ máy nhà nước; chi trả nợ; chi viện trợ và các khoản chi khác theo quy định của pháp luật." },
    { id: "d8", heading: "Điều 8. Nguyên tắc quản lý ngân sách nhà nước", content: "1. Mọi khoản thu, chi ngân sách phải được dự toán, tổng hợp đầy đủ vào ngân sách nhà nước.\n2. Ngân sách nhà nước được quản lý thống nhất, tập trung dân chủ, hiệu quả, tiết kiệm, công khai, minh bạch, công bằng; có phân công, phân cấp quản lý; gắn quyền hạn với trách nhiệm của cơ quan quản lý nhà nước các cấp.\n3. Dự toán ngân sách nhà nước phải được Quốc hội, Hội đồng nhân dân quyết định trước năm ngân sách 01 tháng." },
    { id: "c2", heading: "CHƯƠNG II — NHIỆM VỤ, QUYỀN HẠN CỦA CÁC CƠ QUAN NHÀ NƯỚC", content: "" },
    { id: "d14", heading: "Điều 14. Nhiệm vụ, quyền hạn của Quốc hội", content: "Quốc hội quyết định dự toán ngân sách nhà nước; phân bổ ngân sách trung ương; phê chuẩn quyết toán ngân sách nhà nước; quy định, sửa đổi hoặc bãi bỏ các thứ thuế; quyết định nguyên tắc phân cấp nhiệm vụ thu, chi và quan hệ giữa ngân sách các cấp; quyết định chính sách cơ bản về tài chính, tiền tệ quốc gia." },
    { id: "c3", heading: "CHƯƠNG III — THU VÀ CHI NGÂN SÁCH NHÀ NƯỚC", content: "" },
    { id: "d35", heading: "Điều 35. Thu ngân sách nhà nước", content: "Thu ngân sách nhà nước bao gồm:\n1. Thuế, phí, lệ phí do các tổ chức, cá nhân nộp theo quy định của pháp luật;\n2. Tiền sử dụng đất; tiền cho thuê đất, thuê mặt nước;\n3. Tiền cho thuê và tiền bán tài sản nhà nước;\n4. Thu từ hoạt động sản xuất, kinh doanh của Nhà nước;\n5. Các khoản đóng góp tự nguyện của tổ chức, cá nhân trong nước và ngoài nước;\n6. Các khoản viện trợ không hoàn lại;\n7. Các khoản thu khác theo quy định của pháp luật." },
    { id: "d36", heading: "Điều 36. Chi ngân sách nhà nước", content: "Chi ngân sách nhà nước bao gồm:\n1. Chi đầu tư phát triển;\n2. Chi dự trữ quốc gia;\n3. Chi thường xuyên;\n4. Chi trả nợ lãi;\n5. Chi viện trợ;\n6. Các khoản chi khác theo quy định của pháp luật.\nNguyên tắc: không được dùng ngân sách nhà nước để hỗ trợ hoạt động của các quỹ tài chính nhà nước ngoài ngân sách trừ trường hợp pháp luật có quy định." },
    { id: "c4", heading: "CHƯƠNG IV — LẬP, CHẤP HÀNH VÀ QUYẾT TOÁN NGÂN SÁCH", content: "" },
    { id: "d43", heading: "Điều 43. Lập dự toán ngân sách nhà nước", content: "Căn cứ lập dự toán ngân sách nhà nước:\n1. Nhiệm vụ phát triển kinh tế — xã hội và bảo đảm quốc phòng, an ninh;\n2. Quy định của pháp luật về thuế, phí, lệ phí và các khoản thu khác;\n3. Định mức phân bổ ngân sách, chế độ, tiêu chuẩn, định mức chi ngân sách do cơ quan nhà nước có thẩm quyền quy định;\n4. Chỉ thị của Thủ tướng Chính phủ về việc xây dựng kế hoạch phát triển kinh tế — xã hội và dự toán ngân sách nhà nước năm sau." },
    { id: "end", heading: "ĐIỀU KHOẢN THI HÀNH", content: "Luật này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2017.\nLuật Ngân sách nhà nước số 01/2002/QH11 hết hiệu lực kể từ ngày Luật này có hiệu lực thi hành.\n\nCHỦ TỊCH QUỐC HỘI\nNguyễn Sinh Hùng" },
  ],
};

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function DocTypeBadge({ type }: { type: string }) {
  const map: Record<string, string> = {
    "Nghị định": "bg-blue-50 text-blue-700 border-blue-100",
    "Thông tư": "bg-green-50 text-green-700 border-green-100",
    "Quyết định": "bg-violet-50 text-violet-700 border-violet-100",
    "Luật": "bg-orange-50 text-orange-700 border-orange-100",
    "Nghị quyết": "bg-rose-50 text-rose-700 border-rose-100",
  };
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-semibold tracking-wide ${map[type] ?? "bg-gray-50 text-gray-600 border-gray-100"}`}>
      {type}
    </span>
  );
}

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${status === "Còn hiệu lực" ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-400"}`}>
      {status}
    </span>
  );
}

function SummaryTabs() {
  const [active, setActive] = useState("context");
  const content = SUMMARY_TABS.find(t => t.key === active)?.content ?? "";
  return (
    <div>
      <div className="flex gap-0.5 bg-gray-100 p-1 rounded-xl mb-4 overflow-x-auto">
        {SUMMARY_TABS.map(tab => (
          <button key={tab.key} onClick={() => setActive(tab.key)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${active === tab.key ? "bg-white text-[#C41E3A] shadow-sm" : "text-gray-500 hover:text-gray-700"}`}>
            {tab.label}
          </button>
        ))}
      </div>
      <div className="bg-gray-50 rounded-xl p-4">
        <p className="text-xs text-gray-700 leading-relaxed">{content}</p>
      </div>
    </div>
  );
}

// ─── HIGHLIGHTED TEXT ─────────────────────────────────────────────────────────

function HighlightedText({ text, activeTerm, onTermClick }: {
  text: string;
  activeTerm: string | null;
  onTermClick: (term: string) => void;
}) {
  const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = HIGHLIGHT_TERMS.map(t => escapeRe(t.term)).join("|");
  if (!pattern) return <>{text}</>;
  const parts = text.split(new RegExp(`(${pattern})`, "gi"));
  return (
    <>
      {parts.map((part, i) => {
        const match = HIGHLIGHT_TERMS.find(t => t.term.toLowerCase() === part.toLowerCase());
        if (!match) return <span key={i}>{part}</span>;
        const isActive = activeTerm?.toLowerCase() === match.term.toLowerCase();
        return (
          <span key={i} onClick={() => onTermClick(match.term)}
            className={`cursor-pointer font-semibold underline decoration-dotted transition-all ${isActive ? "bg-yellow-200 text-yellow-900 decoration-yellow-500" : "text-[#C41E3A] decoration-[#C41E3A]/40 hover:bg-red-50"}`}>
            {part}
          </span>
        );
      })}
    </>
  );
}

// ─── DOCUMENT VIEWER MODAL (centered popup) ──────────────────────────────────

function DocumentViewerModal({ onClose, initialTerm }: { onClose: () => void; initialTerm?: string | null }) {
  const [activeTerm, setActiveTerm] = useState<string | null>(initialTerm ?? null);
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const docScrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to initialTerm on mount
  useEffect(() => {
    if (initialTerm) {
      const found = HIGHLIGHT_TERMS.find(t => t.term.toLowerCase() === initialTerm.toLowerCase());
      if (found) {
        setTimeout(() => {
          sectionRefs.current[found.sectionId]?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 250);
      }
    }
  }, []);

  const handleTermClick = (termStr: string) => {
    const found = HIGHLIGHT_TERMS.find(t => t.term.toLowerCase() === termStr.toLowerCase());
    if (!found) return;
    setActiveTerm(termStr);
    setTimeout(() => {
      sectionRefs.current[found.sectionId]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
  };

  const activeTermData = HIGHLIGHT_TERMS.find(t => t.term.toLowerCase() === (activeTerm ?? "").toLowerCase()) ?? null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-6">
      <div className="bg-white rounded-2xl w-full flex flex-col shadow-2xl border border-gray-100 overflow-hidden"
        style={{ maxWidth: 920, height: "88vh" }}>

        {/* ── Fixed header ── */}
        <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#0F1623] rounded-xl flex items-center justify-center shadow-sm">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-gray-900">NĐ 15/2021/NĐ-CP — Văn bản đầy đủ</h2>
              <p className="text-[10px] text-gray-400 mt-0.5">Nhấn vào thuật ngữ bôi đỏ để xem định nghĩa và điều hướng</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Fixed term panel (always visible above document) ── */}
        <div className="flex-shrink-0 border-b border-gray-100 bg-gray-50/70 px-6 py-3 space-y-2.5">
          {/* Term pills */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex-shrink-0">Thuật ngữ quan trọng:</span>
            {HIGHLIGHT_TERMS.map(t => (
              <button key={t.term} onClick={() => handleTermClick(t.term)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-semibold transition-all border ${activeTerm?.toLowerCase() === t.term.toLowerCase() ? "bg-[#C41E3A] text-white border-[#C41E3A] shadow-sm" : "bg-white text-gray-600 border-gray-200 hover:border-[#C41E3A]/40 hover:text-[#C41E3A]"}`}>
                {t.term}
              </button>
            ))}
          </div>

          {/* Active term definition — fixed above document, never overlaps text */}
          {activeTermData ? (
            <div className="flex items-start gap-2.5 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl">
              <Hash className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-amber-900 mb-0.5">{activeTermData.term}</p>
                <p className="text-xs text-amber-800 leading-relaxed">{activeTermData.definition}</p>
              </div>
              <button onClick={() => setActiveTerm(null)} className="text-amber-400 hover:text-amber-600 flex-shrink-0 p-0.5 rounded">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-100 rounded-xl">
              <Lightbulb className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />
              <p className="text-[11px] text-blue-700">Nhấn vào một thuật ngữ ở trên hoặc bôi đỏ trong văn bản để xem định nghĩa chi tiết.</p>
            </div>
          )}
        </div>

        {/* ── Scrollable document text ── */}
        <div ref={docScrollRef} className="flex-1 overflow-y-auto px-8 py-6 space-y-5"
          style={{ fontSize: 13, lineHeight: 1.75, fontFamily: "Georgia, 'Times New Roman', serif" }}>
          {DOCUMENT_SECTIONS.map(sec => (
            <div key={sec.id}
              ref={el => { sectionRefs.current[sec.id] = el; }}
              className={`transition-all duration-300 ${
                activeTerm && HIGHLIGHT_TERMS.find(t => t.sectionId === sec.id && t.term.toLowerCase() === activeTerm.toLowerCase())
                  ? "bg-yellow-50/80 -mx-4 px-4 py-2 rounded-xl border-l-4 border-yellow-400"
                  : ""
              }`}>
              {sec.heading && (
                <p className={`font-bold mb-2 ${sec.heading.startsWith("CHƯƠNG")
                  ? "text-center text-sm uppercase tracking-wide text-[#0F1623] border-b border-gray-200 pb-2 mt-4"
                  : "text-[13px] text-gray-900"}`}>
                  {sec.heading}
                </p>
              )}
              {sec.content && (
                <p className="text-gray-700 whitespace-pre-line">
                  <HighlightedText text={sec.content} activeTerm={activeTerm} onTermClick={handleTermClick} />
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── SHARE MODAL ─────────────────────────────────────────────────────────────

function ShareModal({ onClose }: { onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const [access, setAccess] = useState("view");
  const [email, setEmail] = useState("");
  const handleCopy = () => { setCopied(true); setTimeout(() => setCopied(false), 2000); };

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-[440px] overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <Share2 className="w-4 h-4 text-[#C41E3A]" />
            <h3 className="text-sm font-bold text-gray-900">Chia sẻ tài liệu</h3>
          </div>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-5 space-y-5">
          <div>
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Liên kết chia sẻ</p>
            <div className="flex gap-2">
              <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs text-gray-600 font-mono overflow-hidden">
                <Link className="w-3 h-3 text-gray-400 flex-shrink-0" />
                <span className="truncate">https://vads.gov.vn/doc/nd15-2021-nd-cp</span>
              </div>
              <button onClick={handleCopy} className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all flex-shrink-0 ${copied ? "bg-emerald-500 text-white" : "bg-[#0F1623] hover:bg-[#1a2535] text-white"}`}>
                {copied ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Đã sao chép" : "Sao chép"}
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Quyền truy cập</p>
            <div className="flex gap-2">
              {[{ id: "view", icon: Eye, label: "Chỉ xem" }, { id: "comment", icon: MessageSquare, label: "Bình luận" }, { id: "edit", icon: Users, label: "Chỉnh sửa" }].map(({ id, icon: Icon, label }) => (
                <button key={id} onClick={() => setAccess(id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-semibold border transition-all ${access === id ? "border-[#C41E3A] text-[#C41E3A] bg-[#C41E3A]/5" : "border-gray-200 text-gray-600 hover:border-gray-300"}`}>
                  <Icon className="w-3.5 h-3.5" /> {label}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Mời cộng tác viên</p>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email cộng tác viên..."
                  className="w-full pl-8 pr-3 py-2 text-xs bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-[#C41E3A] transition-colors" />
              </div>
              <button className="px-4 py-2 bg-[#C41E3A] hover:bg-[#a8172f] text-white text-xs font-bold rounded-xl transition-colors flex-shrink-0">Mời</button>
            </div>
          </div>
          <div className="flex items-center gap-2 py-3 px-3 bg-gray-50 rounded-xl">
            <Lock className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            <p className="text-[11px] text-gray-500">Chỉ những người được mời mới có thể xem tài liệu này.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── LAW FULL TEXT MODAL ──────────────────────────────────────────────────────

function LawFullTextModal({ law, onClose }: { law: typeof LEGAL_LIBRARY[0]; onClose: () => void }) {
  const sections = LAW_FULL_TEXT[law.id] ?? [];

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-6">
      <div className="bg-white rounded-2xl w-full flex flex-col shadow-2xl border border-gray-100 overflow-hidden"
        style={{ maxWidth: 860, height: "88vh" }}>

        {/* Header */}
        <div className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#0F1623] rounded-xl flex items-center justify-center shadow-sm">
              <Scale className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-gray-900">{law.name}</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] font-mono text-gray-400">{law.number}</span>
                <span className="text-gray-200">·</span>
                <span className="text-[10px] text-gray-400">{law.issuer}</span>
                <span className="text-gray-200">·</span>
                <StatusPill status={law.status} />
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* TOC strip */}
        <div className="flex-shrink-0 border-b border-gray-100 bg-gray-50/60 px-6 py-2.5 overflow-x-auto">
          <div className="flex items-center gap-2 min-w-max">
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex-shrink-0">Chương:</span>
            {(LAW_DETAILS[law.id]?.chapters ?? []).map((ch, i) => (
              <span key={i} className="text-[10px] px-2.5 py-1 bg-white border border-gray-200 rounded-full text-gray-600 font-semibold whitespace-nowrap">
                {i + 1}. {ch.title.replace(/^(Chương|Phần)\s+[IVX\d]+[:.]?\s*/i, "")}
              </span>
            ))}
          </div>
        </div>

        {/* Scrollable full text */}
        <div className="flex-1 overflow-y-auto px-10 py-7 space-y-5"
          style={{ fontSize: 13, lineHeight: 1.85, fontFamily: "Georgia, 'Times New Roman', serif" }}>
          {sections.length > 0 ? sections.map(sec => (
            <div key={sec.id}>
              {sec.heading && (
                <p className={`font-bold mb-2 ${
                  sec.heading.startsWith("CHƯƠNG") || sec.heading.startsWith("PHẦN")
                    ? "text-center text-sm uppercase tracking-wide text-[#0F1623] border-b border-gray-200 pb-2 mt-6"
                    : sec.heading.startsWith("Điều") || sec.heading.startsWith("Khoản")
                    ? "text-[13px] text-gray-900"
                    : "text-center text-xs uppercase tracking-widest text-gray-500 mt-4"
                }`}>
                  {sec.heading}
                </p>
              )}
              {sec.content && (
                <p className="text-gray-700 whitespace-pre-line leading-[1.9]">{sec.content}</p>
              )}
            </div>
          )) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-20">
              <BookOpen className="w-10 h-10 text-gray-200 mb-3" />
              <p className="text-sm font-semibold text-gray-400">Nội dung văn bản đang được cập nhật</p>
              <p className="text-xs text-gray-300 mt-1">Vui lòng quay lại sau</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── LAW DETAIL VIEW ──────────────────────────────────────────────────────────

function LawDetailView({ law, onBack, onSelectLaw, onGoToTree }: {
  law: typeof LEGAL_LIBRARY[0];
  onBack: () => void;
  onSelectLaw: (l: typeof LEGAL_LIBRARY[0]) => void;
  onGoToTree: () => void;
}) {
  const detail = LAW_DETAILS[law.id];
  const relatedLaws = (detail?.relatedIds ?? []).map(id => LEGAL_LIBRARY.find(l => l.id === id)).filter((l): l is typeof LEGAL_LIBRARY[0] => !!l);
  const [showFullText, setShowFullText] = useState(false);

  return (
    <>
    <div>
      {/* Back */}
      <button onClick={onBack}
        className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-800 transition-colors mb-5 group">
        <ChevronLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />Quay lại thư viện pháp luật
      </button>

      <div className="bg-white rounded-2xl border border-black/[0.05] overflow-hidden shadow-sm">
        {/* Header */}
        <div className="px-6 py-6 border-b border-gray-100">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-[#0F1623] rounded-2xl flex items-center justify-center flex-shrink-0 shadow-md">
              <Scale className="w-6 h-6 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <h2 className="text-base font-bold text-gray-900">{law.name}</h2>
                <StatusPill status={law.status} />
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
                <span className="font-mono font-semibold text-gray-700">{law.number}</span>
                <span>·</span><span>{law.issuer}</span>
                <span>·</span><span>Ban hành năm {law.year}</span>
              </div>
              <span className="mt-2 inline-block text-[10px] px-2.5 py-1 bg-gray-100 text-gray-600 rounded-full font-semibold">{law.category}</span>
            </div>
          </div>
          {detail && <p className="mt-4 text-sm text-gray-600 leading-relaxed">{detail.description}</p>}

          {/* Action buttons */}
          <div className="flex items-center gap-3 mt-5">
            <button
              onClick={() => setShowFullText(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-[#0F1623] hover:bg-[#1a2535] text-white text-xs font-bold rounded-xl transition-colors shadow-sm">
              <BookOpen className="w-3.5 h-3.5" />Xem chi tiết
            </button>
            <button onClick={onGoToTree} className="flex items-center gap-2 px-4 py-2.5 bg-[#C41E3A] hover:bg-[#a8172f] text-white text-xs font-bold rounded-xl transition-colors shadow-sm">
              <GitBranch className="w-3.5 h-3.5" />Tạo sơ đồ tư duy
            </button>
          </div>
        </div>

        {/* Body: chapters + sidebar */}
        <div className="flex divide-x divide-gray-100">
          {/* Chapters */}
          <div className="flex-1 p-6">
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-4">Cấu trúc văn bản</h3>
            <div className="space-y-2.5">
              {detail?.chapters.map((ch, i) => (
                <div key={i} className="flex items-start gap-3 p-3.5 bg-gray-50 rounded-xl hover:bg-gray-100 cursor-pointer transition-colors group">
                  <div className="w-6 h-6 bg-[#0F1623] group-hover:bg-[#C41E3A] rounded-md flex items-center justify-center flex-shrink-0 text-[10px] text-white font-bold transition-colors">{i + 1}</div>
                  <div>
                    <p className="text-xs font-bold text-gray-800 mb-0.5">{ch.title}</p>
                    <p className="text-[11px] text-gray-500 leading-relaxed">{ch.summary}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Related laws + keywords */}
          <div className="flex-shrink-0 p-6" style={{ width: 272 }}>
            <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-4">Văn bản liên quan</h3>
            <div className="space-y-2 mb-6">
              {relatedLaws.map((rel) => (
                <button key={rel.id} onClick={() => onSelectLaw(rel)}
                  className="w-full flex items-center gap-3 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 cursor-pointer transition-colors group text-left">
                  <Scale className="w-4 h-4 text-gray-300 group-hover:text-[#C41E3A] flex-shrink-0 transition-colors" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-semibold text-gray-700 line-clamp-2 leading-snug">{rel.name}</p>
                    <div className="mt-1"><StatusPill status={rel.status} /></div>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-gray-300 group-hover:text-[#C41E3A] flex-shrink-0 transition-colors" />
                </button>
              ))}
            </div>
            {detail?.keywords && (
              <>
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3">Từ khóa</h3>
                <div className="flex flex-wrap gap-1.5">
                  {detail.keywords.map(kw => (
                    <span key={kw} className="text-[10px] px-2.5 py-1 bg-[#0F1623]/8 text-[#0F1623] rounded-full font-semibold">{kw}</span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>

    {showFullText && <LawFullTextModal law={law} onClose={() => setShowFullText(false)} />}
    </>
  );
}

// ─── SIDEBAR ─────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "documents", label: "Tài liệu của tôi", icon: FileText },
  { id: "library", label: "Thư viện pháp luật", icon: Scale },
  { id: "notebook", label: "Sổ tay kiến thức", icon: BookMarked },
];

// ─── PROFILE MODAL ───────────────────────────────────────────────────────────

function ProfileModal({ onClose, currentUser, onChanged }: {
  onClose: () => void;
  currentUser: UserPublic;
  onChanged: () => void;
}) {
  const [tab, setTab] = useState<"info" | "password">("info");
  const [phone, setPhone] = useState("");
  const [chucVu, setChucVu] = useState(currentUser.position ?? "");
  const [phongBan, setPhongBan] = useState(currentUser.department ?? "");
  const [thon, setThon] = useState("");
  const [xa, setXa] = useState(currentUser.commune_id);
  const [tinh, setTinh] = useState("");
  const [saved, setSaved] = useState(false);
  const [curPwd, setCurPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [pwdSaved, setPwdSaved] = useState(false);

  const handleSaveInfo = () => { setSaved(true); setTimeout(() => setSaved(false), 2000); };
  const handleSavePwd = () => {
    if (!curPwd || !newPwd || newPwd !== confirmPwd) return;
    void changePassword(curPwd, newPwd)
      .then(() => {
        setPwdSaved(true);
        setCurPwd(""); setNewPwd(""); setConfirmPwd("");
        setTimeout(() => { setPwdSaved(false); onChanged(); }, 2000);
      })
      .catch(reason => window.alert(reason instanceof Error ? reason.message : "Không thể đổi mật khẩu."));
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 w-full" style={{ maxWidth: 520 }}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#C41E3A] to-[#8a1224] flex items-center justify-center text-white font-bold">NV</div>
            <div>
              <h2 className="text-sm font-bold text-gray-900">{currentUser.full_name}</h2>
              <p className="text-[10px] text-gray-400">{currentUser.email}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"><X className="w-4 h-4" /></button>
        </div>

        <div className="flex border-b border-gray-100 px-6">
          {([["info", "Thông tin cá nhân", User], ["password", "Đổi mật khẩu", Lock]] as const).map(([key, label, Icon]) => (
            <button key={key} onClick={() => setTab(key)}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition-colors ${tab === key ? "border-[#C41E3A] text-[#C41E3A]" : "border-transparent text-gray-400 hover:text-gray-600"}`}>
              <Icon className="w-3.5 h-3.5" />{label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {tab === "info" ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Họ và tên</label>
                  <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-400 select-none">{currentUser.full_name}</div>
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Email</label>
                  <div className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-400 select-none">{currentUser.email}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {([["Số điện thoại", phone, setPhone, Phone], ["Chức vụ", chucVu, setChucVu, Briefcase]] as const).map(([label, val, setter, Icon]) => (
                  <div key={label}>
                    <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{label}</label>
                    <div className="relative">
                      <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-300" />
                      <input value={val} onChange={e => setter(e.target.value)} className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Phòng ban</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-300" />
                  <input value={phongBan} onChange={e => setPhongBan(e.target.value)} className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-colors" />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {([["Thôn", thon, setThon, "VD: Thôn 1"], ["Xã", xa, setXa, ""], ["Tỉnh", tinh, setTinh, ""]] as const).map(([label, val, setter, ph]) => (
                  <div key={label}>
                    <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{label}</label>
                    <div className="relative">
                      <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-300" />
                      <input value={val} onChange={e => setter(e.target.value)} placeholder={ph} className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-colors" />
                    </div>
                  </div>
                ))}
              </div>
              <button onClick={handleSaveInfo}
                className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all ${saved ? "bg-emerald-500 text-white" : "bg-[#0F1623] hover:bg-[#1a2535] text-white"}`}>
                {saved ? <><CheckCircle2 className="w-3.5 h-3.5" />Đã lưu</> : <><Save className="w-3.5 h-3.5" />Lưu thay đổi</>}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {[["Mật khẩu hiện tại", curPwd, setCurPwd], ["Mật khẩu mới", newPwd, setNewPwd], ["Xác nhận mật khẩu mới", confirmPwd, setConfirmPwd]].map(([label, val, setter]) => (
                <div key={label as string}>
                  <label className="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1.5">{label as string}</label>
                  <input type="password" value={val as string} onChange={e => (setter as (v: string) => void)(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-colors" />
                </div>
              ))}
              {newPwd && confirmPwd && newPwd !== confirmPwd && (
                <p className="text-[11px] text-red-500 flex items-center gap-1"><AlertCircle className="w-3 h-3" />Mật khẩu xác nhận không khớp</p>
              )}
              <button onClick={handleSavePwd} disabled={!curPwd || !newPwd || newPwd !== confirmPwd}
                className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all ${pwdSaved ? "bg-emerald-500 text-white" : "bg-[#0F1623] hover:bg-[#1a2535] text-white"} disabled:opacity-40 disabled:cursor-not-allowed`}>
                {pwdSaved ? <><CheckCircle2 className="w-3.5 h-3.5" />Đã đổi mật khẩu</> : <><Lock className="w-3.5 h-3.5" />Đổi mật khẩu</>}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── IMPORT MODAL ─────────────────────────────────────────────────────────────

function ImportModal({ onClose, onSubmit, currentUser }: {
  onClose: () => void;
  onSubmit: (data: ImportData) => void;
  currentUser: UserPublic;
}) {
  const [ten, setTen] = useState(currentUser.full_name);
  const [chucVu, setChucVu] = useState(currentUser.position ?? "");
  const [phongBan, setPhongBan] = useState(currentUser.department ?? "");
  const [thon, setThon] = useState("");
  const [xa, setXa] = useState(currentUser.commune_id);
  const [tinh, setTinh] = useState("");
  const [baoCaoFile, setBaoCaoFile] = useState<string | null>(null);
  const [vanBanFile, setVanBanFile] = useState<string | null>(null);
  const baoCaoRef = useRef<HTMLInputElement>(null);
  const vanBanRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = (type: "baoCao" | "vanBan", files: FileList | null) => {
    if (!files?.[0]) return;
    const file = files[0];
    if (type === "baoCao") setBaoCaoFile(file.name);
    else setVanBanFile(file.name);
    void uploadLegacyDocument(file)
      .then(() => window.dispatchEvent(new Event("vads:documents-changed")))
      .catch(reason => {
        if (type === "baoCao") setBaoCaoFile(null);
        else setVanBanFile(null);
        window.alert(reason instanceof Error ? reason.message : "Không thể tải tài liệu lên.");
      });
  };

  const handleSubmit = () => {
    onSubmit({ ten, chucVu, phongBan, thon, xa, tinh, baoCaoFile, vanBanFile });
    onClose();
  };

  const UploadZone = ({ label, file, onClear, inputRef, type, accent }: {
    label: string; file: string | null; onClear: () => void;
    inputRef: React.RefObject<HTMLInputElement>; type: "baoCao" | "vanBan"; accent?: boolean;
  }) => (
    <div>
      <label className="block text-xs font-semibold text-gray-700 mb-2">{label}</label>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={e => e.preventDefault()}
        onDrop={e => { e.preventDefault(); handleFileDrop(type, e.dataTransfer.files); }}
        className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors min-h-[120px] ${file ? "border-emerald-300 bg-emerald-50" : accent ? "border-[#C41E3A]/30 hover:border-[#C41E3A]/60 hover:bg-red-50/30" : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"}`}
      >
        <input ref={inputRef} type="file" className="hidden" accept=".pdf,.doc,.docx" onChange={e => handleFileDrop(type, e.target.files)} />
        {file ? (
          <>
            <CheckCircle2 className="w-7 h-7 text-emerald-500" />
            <p className="text-xs font-semibold text-emerald-700 text-center break-all px-2">{file}</p>
            <button onClick={e => { e.stopPropagation(); onClear(); }} className="text-[10px] text-gray-400 hover:text-red-500 transition-colors mt-1">Xóa tệp</button>
          </>
        ) : (
          <>
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${accent ? "bg-[#C41E3A]/10" : "bg-gray-100"}`}>
              <FileUp className={`w-5 h-5 ${accent ? "text-[#C41E3A]" : "text-gray-400"}`} />
            </div>
            <p className="text-xs font-semibold text-gray-600">Kéo thả hoặc nhấp để tải lên</p>
            <p className="text-[10px] text-gray-400">PDF, DOC, DOCX</p>
          </>
        )}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-100 w-full flex flex-col" style={{ maxWidth: 680, maxHeight: "90vh" }}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[#C41E3A] rounded-xl flex items-center justify-center shadow-sm">
              <Upload className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-gray-900">Import tài liệu phân tích</h2>
              <p className="text-[10px] text-gray-400">Nhập thông tin và tải lên văn bản cần phân tích</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"><X className="w-4 h-4" /></button>
        </div>

        <div className="overflow-y-auto p-6 space-y-5 flex-1">
          <div>
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-3">Thông tin người dùng</p>
            <div className="grid grid-cols-2 gap-3">
              {([["Tên", ten, setTen, User], ["Chức vụ", chucVu, setChucVu, Briefcase], ["Phòng ban", phongBan, setPhongBan, Building2]] as const).map(([label, val, setter, Icon]) => (
                <div key={label} className={label === "Phòng ban" ? "col-span-2" : ""}>
                  <label className="block text-[11px] font-semibold text-gray-500 mb-1.5">{label}</label>
                  <div className="relative">
                    <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-300" />
                    <input value={val} onChange={e => setter(e.target.value)} className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-colors" />
                  </div>
                </div>
              ))}
              {([["Thôn", thon, setThon, "VD: Thôn 1"], ["Xã", xa, setXa, ""], ["Tỉnh", tinh, setTinh, ""]] as const).map(([label, val, setter, ph]) => (
                <div key={label}>
                  <label className="block text-[11px] font-semibold text-gray-500 mb-1.5">{label}</label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-300" />
                    <input value={val} onChange={e => setter(e.target.value)} placeholder={ph} className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="text-[11px] font-bold text-gray-400 uppercase tracking-widest mb-3">Tài liệu cần phân tích</p>
            <div className="grid grid-cols-2 gap-4">
              <UploadZone label="Báo cáo thực trạng" file={baoCaoFile} onClear={() => setBaoCaoFile(null)} inputRef={baoCaoRef} type="baoCao" />
              <UploadZone label="Văn bản hành chính" file={vanBanFile} onClear={() => setVanBanFile(null)} inputRef={vanBanRef} type="vanBan" accent />
            </div>
          </div>
        </div>

        <div className="border-t border-gray-100 px-6 py-4 flex-shrink-0 flex items-center justify-between gap-4">
          <p className="text-[10px] text-gray-400 leading-relaxed flex-1">AI sẽ phân tích và đề xuất phương án phù hợp với chức vụ, phòng ban và địa phương của bạn</p>
          <button onClick={handleSubmit}
            className="flex items-center gap-2 bg-[#C41E3A] hover:bg-[#a8172f] text-white px-6 py-2.5 rounded-xl text-xs font-bold transition-colors shadow-md whitespace-nowrap flex-shrink-0">
            <Brain className="w-3.5 h-3.5" />Bắt đầu phân tích
          </button>
        </div>
      </div>
    </div>
  );
}

function Sidebar({ active, onNavigate, collapsed, onToggle, onProfile, onImport }: {
  active: string;
  onNavigate: (s: Screen) => void;
  collapsed: boolean;
  onToggle: () => void;
  onProfile: () => void;
  onImport: () => void;
}) {
  const [hoverOpen, setHoverOpen] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout>>();

  const onEnter = () => {
    clearTimeout(hoverTimer.current);
    if (collapsed) setHoverOpen(true);
  };
  const onLeave = () => {
    hoverTimer.current = setTimeout(() => { setHoverOpen(false); }, 180);
  };

  // Single sidebar — expands either permanently (!collapsed) or temporarily (hoverOpen)
  const isExpanded = !collapsed || hoverOpen;

  return (
    <aside
      className="fixed left-0 top-0 h-full bg-[#0F1623] flex flex-col z-30 overflow-hidden transition-[width] duration-200 ease-out shadow-xl"
      style={{ width: isExpanded ? 232 : 64 }}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-2.5 border-b border-white/8 h-14 px-3 flex-shrink-0">
        {/* Logo mark — click to permanently toggle */}
        <button
          onClick={() => { onToggle(); setHoverOpen(false); }}
          title={collapsed ? "Mở rộng" : "Thu gọn"}
          className="w-8 h-8 bg-[#C41E3A] hover:bg-[#a8172f] rounded-lg flex items-center justify-center flex-shrink-0 shadow-sm transition-colors"
        >
          <Scale className="w-4 h-4 text-white" />
        </button>

        {/* Brand text — only visible when expanded */}
        {isExpanded && (
          <div className="flex-1 flex items-center justify-between min-w-0 overflow-hidden">
            <div className="min-w-0">
              <div className="text-white font-bold text-sm leading-tight tracking-wide whitespace-nowrap">VADS</div>
              <div className="text-white/35 text-[7px] uppercase tracking-widest whitespace-nowrap">Vietnamese Admin Doc System</div>
            </div>
            {/* Show collapse arrow only when permanently expanded */}
            {!collapsed && (
              <button onClick={onToggle} className="p-1.5 text-white/40 hover:text-white/80 hover:bg-white/8 rounded-lg transition-colors flex-shrink-0 ml-1">
                <ChevronLeft className="w-4 h-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Import button ── */}
      <div className="flex-shrink-0 px-2.5 pt-4 pb-2">
        <button
          onClick={() => { onImport(); setHoverOpen(false); }}
          title="Import file"
          className="w-full bg-[#C41E3A] hover:bg-[#a8172f] text-white rounded-xl flex items-center justify-center gap-2 font-semibold transition-colors shadow-md overflow-hidden"
          style={{ padding: isExpanded ? "10px 16px" : "10px" }}
        >
          <Upload className="w-4 h-4 flex-shrink-0" />
          {isExpanded && <span className="text-sm whitespace-nowrap">Import file</span>}
        </button>
      </div>

      {/* ── Nav items ── */}
      <nav className="flex-1 py-2 space-y-0.5 overflow-y-auto px-2">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const isActive = active === id;
          return (
            <button key={id}
              onClick={() => { onNavigate(id as Screen); setHoverOpen(false); }}
              title={!isExpanded ? label : undefined}
              className={`w-full flex items-center rounded-xl transition-all text-left overflow-hidden ${isExpanded ? "gap-3 px-3 py-2.5" : "justify-center p-2.5"} ${isActive ? "bg-white/10 text-white" : "text-white/50 hover:bg-white/6 hover:text-white/80"}`}
            >
              {isExpanded && (
                <div className={`flex-shrink-0 w-0.5 h-4 rounded-full ${isActive ? "bg-[#C41E3A]" : "bg-transparent"}`} />
              )}
              <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? "text-white" : "text-white/40"}`} />
              {isExpanded && <span className="truncate text-sm">{label}</span>}
            </button>
          );
        })}
      </nav>

      {/* ── User ── */}
      <div className={`border-t border-white/8 flex-shrink-0 overflow-hidden ${isExpanded ? "px-4 py-4" : "p-2"}`}>
        {isExpanded ? (
          <div className="flex items-center gap-3">
            <button onClick={onProfile} title="Thông tin cá nhân"
              className="w-8 h-8 rounded-full bg-gradient-to-br from-[#C41E3A] to-[#8a1224] flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0 hover:opacity-80 transition-opacity">NV</button>
            <button onClick={onProfile} className="flex-1 min-w-0 text-left hover:opacity-80 transition-opacity">
              <div className="text-white text-xs font-semibold truncate whitespace-nowrap">Nguyễn Văn An</div>
              <div className="text-white/35 text-[10px] truncate whitespace-nowrap">Chuyên viên pháp chế</div>
            </button>
            <button className="text-white/30 hover:text-white/70 transition-colors p-1 rounded flex-shrink-0">
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="flex justify-center">
            <button onClick={onProfile} title="Thông tin cá nhân"
              className="w-8 h-8 rounded-full bg-gradient-to-br from-[#C41E3A] to-[#8a1224] flex items-center justify-center text-white text-[10px] font-bold hover:opacity-80 transition-opacity">NV</button>
          </div>
        )}
      </div>
    </aside>
  );
}

// ─── HEADER ──────────────────────────────────────────────────────────────────

function Header({ title, sidebarW }: { title: string; sidebarW: number }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [showNotif, setShowNotif] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  const allDocs = [
    ...MY_DOCUMENTS.map(d => ({ ...d, source: "mine" as const })),
    ...LEGAL_LIBRARY.map(d => ({ id: d.id, name: d.name, type: d.category, date: String(d.year), month: "", year: d.year, source: "library" as const })),
  ];
  const results = searchQuery.length > 1
    ? allDocs.filter(d => d.name.toLowerCase().includes(searchQuery.toLowerCase())).slice(0, 6)
    : [];

  useEffect(() => {
    const h = (e: MouseEvent) => { if (searchRef.current && !searchRef.current.contains(e.target as Node)) setShowSearch(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  return (
    <header className="fixed top-0 right-0 h-14 bg-white border-b border-black/[0.06] flex items-center pr-5 z-20 transition-all duration-300" style={{ left: sidebarW }}>
      <h1 className="text-[15px] font-bold text-gray-900 flex-1 pl-6">{title}</h1>

      {/* Search */}
      <div ref={searchRef} className="relative mr-2">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
        <input value={searchQuery} onChange={e => { setSearchQuery(e.target.value); setShowSearch(true); }}
          onFocus={() => setShowSearch(true)} placeholder="Tìm kiếm tài liệu..."
          className="pl-8 pr-3 py-1.5 text-xs bg-gray-50 border border-gray-200 rounded-lg w-52 focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-colors" />
        {showSearch && results.length > 0 && (
          <div className="absolute top-full left-0 mt-1.5 bg-white border border-gray-200 rounded-xl shadow-xl z-30 w-72 overflow-hidden py-1">
            {results.map((d, i) => (
              <button key={i} className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-50 text-left transition-colors">
                <FileText className="w-4 h-4 text-gray-300 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-gray-800 truncate">{d.name}</p>
                  <p className="text-[10px] text-gray-400">{d.type} · {d.source === "mine" ? "Tài liệu của tôi" : "Thư viện"}</p>
                </div>
              </button>
            ))}
          </div>
        )}
        {showSearch && searchQuery.length > 1 && results.length === 0 && (
          <div className="absolute top-full left-0 mt-1.5 bg-white border border-gray-200 rounded-xl shadow-xl z-30 w-60 p-4 text-center">
            <p className="text-xs text-gray-500">Không tìm thấy kết quả</p>
          </div>
        )}
      </div>

      {/* Notifications */}
      <div className="relative">
        <button onClick={() => setShowNotif(v => !v)} className="relative p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-[#C41E3A] rounded-full" />
        </button>
        {showNotif && (
          <div className="absolute right-0 top-full mt-2 bg-white border border-gray-200 rounded-2xl shadow-xl z-30 w-80 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wide">Thông báo</h3>
              <span className="text-[10px] text-[#C41E3A] font-semibold">3 mới</span>
            </div>
            <div className="max-h-72 overflow-y-auto">
              {MY_DOCUMENTS.slice(0, 3).map((doc, i) => (
                <div key={i} className="flex items-start gap-3 px-4 py-3 border-b border-gray-50 hover:bg-gray-50 transition-colors cursor-pointer">
                  <div className="w-8 h-8 bg-[#C41E3A]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText className="w-3.5 h-3.5 text-[#C41E3A]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-gray-800 line-clamp-2">{doc.name}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">Đã thêm · {doc.date}</p>
                  </div>
                  <div className="w-1.5 h-1.5 bg-[#C41E3A] rounded-full flex-shrink-0 mt-1.5" />
                </div>
              ))}
            </div>
            <button onClick={() => setShowNotif(false)} className="w-full py-2.5 text-center text-xs font-semibold text-[#C41E3A] hover:bg-gray-50 transition-colors">
              Xem tất cả thông báo
            </button>
          </div>
        )}
      </div>

    </header>
  );
}

function MainLayout({ children, active, title, onNavigate, collapsed, onToggle, onProfile, onImport }: {
  children: React.ReactNode;
  active: string;
  title: string;
  onNavigate: (s: Screen) => void;
  collapsed: boolean;
  onToggle: () => void;
  onProfile: () => void;
  onImport: () => void;
}) {
  const W = collapsed ? 64 : 232;
  return (
    <div className="min-h-screen bg-[#F4F5F7]">
      <Sidebar active={active} onNavigate={onNavigate} collapsed={collapsed} onToggle={onToggle} onProfile={onProfile} onImport={onImport} />
      <Header title={title} sidebarW={W} />
      <main className="pt-14 min-h-screen transition-all duration-300" style={{ marginLeft: W }}>
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}

// ─── LOGIN ────────────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => { setLoading(false); onLogin(); }, 1400);
  };

  return (
    <div className="min-h-screen bg-[#F4F5F7] flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-[#C41E3A]/6 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-[#0F1623]/8 rounded-full blur-3xl pointer-events-none" />
      <div className="relative w-full max-w-[380px]">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-[#0F1623] rounded-2xl shadow-xl mb-4">
            <Scale className="w-7 h-7 text-white" />
          </div>
          <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1.5 font-semibold">Vietnamese Administrative Document System</div>
          <h1 className="text-3xl font-bold text-gray-900" style={{ fontFamily: "'Playfair Display', serif" }}>VADS</h1>
        </div>
        <div className="bg-white rounded-2xl shadow-[0_4px_32px_rgba(0,0,0,0.08)] border border-black/[0.05] p-8">
          <h2 className="text-base font-bold text-gray-900 mb-6">Đăng nhập hệ thống</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Tài khoản</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="email@congty.vn"
                className="w-full px-3.5 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-all bg-gray-50/70" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">Mật khẩu</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••"
                className="w-full px-3.5 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] transition-all bg-gray-50/70" />
            </div>
            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center gap-2 text-gray-600 cursor-pointer select-none">
                <input type="checkbox" style={{ accentColor: "#C41E3A" }} />Ghi nhớ đăng nhập
              </label>
              <a href="#" className="text-[#C41E3A] font-semibold hover:underline">Quên mật khẩu?</a>
            </div>
            <button type="submit" disabled={loading}
              className="w-full bg-[#C41E3A] hover:bg-[#a8172f] disabled:opacity-60 text-white py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2 shadow-md shadow-[#C41E3A]/25 mt-2">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? "Đang xác thực..." : "Đăng nhập"}
            </button>
          </form>
        </div>
        <p className="text-center text-[10px] text-gray-400 mt-6">© 2025 VADS · Hệ thống phân tích tài liệu hành chính Việt Nam</p>
      </div>
    </div>
  );
}

// ─── DASHBOARD ────────────────────────────────────────────────────────────────

function DashboardScreen({ onNavigate, onAnalyzeUploaded }: {
  onNavigate: (s: Screen) => void;
  onAnalyzeUploaded: () => void;
}) {
  const [baoCaoFile, setBaoCaoFile] = useState<string | null>(null);
  const [vanBanFile, setVanBanFile] = useState<string | null>(null);
  const baoCaoRef = useRef<HTMLInputElement>(null);
  const vanBanRef = useRef<HTMLInputElement>(null);
  const receiveFile = async (
    file: File,
    setName: React.Dispatch<React.SetStateAction<string | null>>,
  ) => {
    setName(file.name);
    try {
      await uploadLegacyDocument(file);
      window.dispatchEvent(new Event("vads:documents-changed"));
    } catch (reason) {
      setName(null);
      window.alert(reason instanceof Error ? reason.message : "Không thể tải tài liệu lên.");
    }
  };
  const CARDS = [
    { id: "documents", title: "Tài liệu của tôi", desc: "Quản lý và tra cứu toàn bộ tài liệu đã phân tích trong hệ thống.", icon: FileText, count: `${MY_DOCUMENTS.length} tài liệu` },
    { id: "library", title: "Thư viện pháp luật", desc: "Tra cứu toàn bộ văn bản pháp luật hiện hành và đã hết hiệu lực.", icon: Scale, count: `${LEGAL_LIBRARY.length} văn bản` },
    { id: "notebook", title: "Sổ tay kiến thức", desc: "Lưu trữ thuật ngữ và định nghĩa pháp lý được trích xuất tự động.", icon: BookMarked, count: `${KNOWLEDGE_TERMS.length} mục từ` },
  ];
  return (
    <div className="space-y-5">
      <div className="relative rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 pt-5 pb-4 border-b border-gray-50">
          <div className="w-8 h-8 bg-[#0F1623] rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm">
            <Upload className="w-3.5 h-3.5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-900">Tải lên tài liệu phân tích</h3>
            <p className="text-[10px] text-gray-400 mt-0.5">Tải đủ 2 tài liệu để AI phân tích và đề xuất phương án phù hợp</p>
          </div>
        </div>

        {/* Two upload zones */}
        <div className="grid grid-cols-2 gap-4 p-5">
          {/* Báo cáo thực trạng */}
          <div>
            <p className="text-[11px] font-bold text-gray-500 uppercase tracking-wide mb-2">Báo cáo thực trạng</p>
            <div
              onClick={() => baoCaoRef.current?.click()}
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) void receiveFile(f, setBaoCaoFile); }}
              className={`rounded-xl border-2 border-dashed cursor-pointer flex flex-col items-center justify-center py-8 px-4 transition-all ${baoCaoFile ? "border-emerald-300 bg-emerald-50" : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"}`}
            >
              <input ref={baoCaoRef} type="file" className="hidden" accept=".pdf,.doc,.docx" onChange={e => { if (e.target.files?.[0]) void receiveFile(e.target.files[0], setBaoCaoFile); }} />
              {baoCaoFile ? (
                <>
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
                  <p className="text-xs font-semibold text-emerald-700 text-center break-all px-1 leading-snug">{baoCaoFile}</p>
                  <button onClick={e => { e.stopPropagation(); setBaoCaoFile(null); }} className="text-[10px] text-gray-400 hover:text-red-500 mt-2 transition-colors">Xóa tệp</button>
                </>
              ) : (
                <>
                  <div className="w-10 h-10 bg-gray-100 rounded-xl flex items-center justify-center mb-3">
                    <FileUp className="w-5 h-5 text-gray-400" />
                  </div>
                  <p className="text-xs font-semibold text-gray-600 text-center">Kéo thả hoặc nhấp để tải lên</p>
                  <p className="text-[10px] text-gray-400 mt-1">PDF, DOC, DOCX</p>
                </>
              )}
            </div>
          </div>

          {/* Văn bản hành chính */}
          <div>
            <p className="text-[11px] font-bold text-gray-500 uppercase tracking-wide mb-2">Văn bản hành chính</p>
            <div
              onClick={() => vanBanRef.current?.click()}
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) void receiveFile(f, setVanBanFile); }}
              className={`rounded-xl border-2 border-dashed cursor-pointer flex flex-col items-center justify-center py-8 px-4 transition-all ${vanBanFile ? "border-emerald-300 bg-emerald-50" : "border-gray-200 hover:border-[#C41E3A]/50 hover:bg-red-50/30"}`}
            >
              <input ref={vanBanRef} type="file" className="hidden" accept=".pdf,.doc,.docx" onChange={e => { if (e.target.files?.[0]) void receiveFile(e.target.files[0], setVanBanFile); }} />
              {vanBanFile ? (
                <>
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
                  <p className="text-xs font-semibold text-emerald-700 text-center break-all px-1 leading-snug">{vanBanFile}</p>
                  <button onClick={e => { e.stopPropagation(); setVanBanFile(null); }} className="text-[10px] text-gray-400 hover:text-red-500 mt-2 transition-colors">Xóa tệp</button>
                </>
              ) : (
                <>
                  <div className="w-10 h-10 bg-[#C41E3A]/10 rounded-xl flex items-center justify-center mb-3">
                    <FileUp className="w-5 h-5 text-[#C41E3A]" />
                  </div>
                  <p className="text-xs font-semibold text-gray-600 text-center">Kéo thả hoặc nhấp để tải lên</p>
                  <p className="text-[10px] text-gray-400 mt-1">PDF, DOC, DOCX</p>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 pb-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            {baoCaoFile && <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-semibold whitespace-nowrap"><CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />Báo cáo đã tải</span>}
            {vanBanFile && <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-semibold whitespace-nowrap"><CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />Văn bản đã tải</span>}
            {!baoCaoFile && !vanBanFile && <p className="text-[11px] text-gray-400">Cần tải lên đủ 2 tài liệu để bắt đầu phân tích</p>}
          </div>
          <button
            disabled={!baoCaoFile || !vanBanFile}
            onClick={() => { onAnalyzeUploaded(); onNavigate("processing"); }}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap flex-shrink-0 ${baoCaoFile && vanBanFile ? "bg-[#C41E3A] hover:bg-[#a8172f] text-white shadow-md shadow-[#C41E3A]/25" : "bg-gray-100 text-gray-400 cursor-not-allowed"}`}
          >
            <Brain className="w-3.5 h-3.5" />Bắt đầu phân tích
          </button>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4">
        {CARDS.map(({ id, title, desc, icon: Icon, count }) => (
          <div key={id} className="bg-white rounded-2xl p-5 border border-black/[0.05] hover:shadow-lg hover:shadow-black/[0.06] transition-all duration-200 group cursor-pointer">
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 bg-[#0F1623] group-hover:bg-[#C41E3A] rounded-xl flex items-center justify-center transition-colors duration-200 shadow-sm">
                <Icon className="w-5 h-5 text-white" />
              </div>
              <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wide bg-gray-50 px-2.5 py-1 rounded-full">{count}</span>
            </div>
            <h3 className="font-bold text-gray-900 text-sm mb-1.5">{title}</h3>
            <p className="text-xs text-gray-500 leading-relaxed mb-4">{desc}</p>
            <button onClick={() => onNavigate(id as Screen)} className="flex items-center gap-1.5 text-[#C41E3A] text-xs font-bold hover:gap-3 transition-all duration-200">
              Truy cập <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── MY DOCUMENTS ─────────────────────────────────────────────────────────────

function MyDocumentsScreen({ onNavigate, onSelectDocument }: {
  onNavigate: (s: Screen) => void;
  onSelectDocument: (document: LegacyDocument) => void;
}) {
  const years = [...new Set(MY_DOCUMENTS.map(document => String(document.year)))]
    .sort((left, right) => Number(right) - Number(left));
  const [year, setYear] = useState(years[0] ?? String(new Date().getFullYear()));
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (years.length > 0 && !years.includes(year)) setYear(years[0]);
  }, [year, years]);
  const months = [...new Set(MY_DOCUMENTS.map(document => document.month))]
    .sort((left, right) => Number(right.replace("Tháng ", "")) - Number(left.replace("Tháng ", "")));
  const grouped = months.map(m => ({ month: m, docs: MY_DOCUMENTS.filter(d => d.month === m && d.year.toString() === year) }));
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Tài liệu của tôi</h2>
          <p className="text-sm text-gray-500 mt-0.5">{MY_DOCUMENTS.filter(d => d.year.toString() === year).length} tài liệu trong năm {year}</p>
        </div>
        <div className="relative">
          <button onClick={() => setOpen(v => !v)} className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 hover:border-gray-300 shadow-sm">
            <Calendar className="w-4 h-4 text-gray-400" />Năm {year}<ChevronDown className="w-4 h-4 text-gray-400" />
          </button>
          {open && (
            <div className="absolute right-0 mt-1.5 bg-white border border-gray-200 rounded-xl shadow-xl z-10 overflow-hidden py-1">
              {years.map(y => (
                <button key={y} onClick={() => { setYear(y); setOpen(false); }}
                  className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${year === y ? "text-[#C41E3A] font-bold" : "text-gray-700"}`}>{y}</button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="space-y-8">
        {grouped.map(({ month, docs }) => docs.length > 0 && (
          <div key={month}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-2 h-2 rounded-full bg-[#C41E3A] flex-shrink-0" />
              <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">{month}</h3>
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-[10px] text-gray-400 font-semibold">{docs.length} tài liệu</span>
            </div>
            <div className="grid grid-cols-3 gap-3 ml-5">
              {docs.map(doc => (
                <div key={doc.id} onClick={() => { onSelectDocument(doc); onNavigate("processing"); }}
                  className="bg-white border border-black/[0.05] rounded-xl p-4 hover:shadow-md hover:border-[#C41E3A]/20 cursor-pointer transition-all group">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 bg-gray-50 group-hover:bg-[#C41E3A]/8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors">
                      <FileText className="w-4 h-4 text-gray-300 group-hover:text-[#C41E3A] transition-colors" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-800 line-clamp-2 mb-2.5 leading-relaxed">{doc.name}</p>
                      <div className="flex items-center justify-between gap-2">
                        <DocTypeBadge type={doc.type} />
                        <span className="text-[9px] text-gray-400 font-mono">{doc.date}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── LEGAL LIBRARY ────────────────────────────────────────────────────────────

function LibDropBtn({ label, value, opts, openKey, activeKey, onOpen, onChange }: {
  label: string; value: string; opts: string[];
  openKey: string; activeKey: string | null;
  onOpen: (k: string | null) => void;
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative">
      <button onClick={e => { e.stopPropagation(); onOpen(activeKey === openKey ? null : openKey); }}
        className="flex items-center gap-2 px-3.5 py-2 bg-white border border-gray-200 rounded-xl text-xs text-gray-700 shadow-sm min-w-[120px]">
        <span className="flex-1 text-left font-medium">{value === "Tất cả" ? label : value}</span>
        <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      </button>
      {activeKey === openKey && (
        <div className="absolute top-full left-0 mt-1.5 bg-white border border-gray-200 rounded-xl shadow-xl z-20 min-w-full overflow-hidden py-1">
          {opts.map(opt => (
            <button key={opt} onClick={e => { e.stopPropagation(); onChange(opt); onOpen(null); }}
              className={`block w-full text-left px-4 py-2 text-xs hover:bg-gray-50 ${value === opt ? "text-[#C41E3A] font-bold" : "text-gray-700"}`}>{opt}</button>
          ))}
        </div>
      )}
    </div>
  );
}

function LegalLibraryScreen({ onNavigate, onSelectDocument }: {
  onNavigate: (s: Screen) => void;
  onSelectDocument: (document: LegacyDocument) => void;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("Tất cả");
  const [status, setStatus] = useState("Tất cả");
  const [year, setYear] = useState("Tất cả");
  const [openDrop, setOpenDrop] = useState<string | null>(null);
  const [selectedLaw, setSelectedLaw] = useState<typeof LEGAL_LIBRARY[0] | null>(null);

  const cats = ["Tất cả", ...new Set(LEGAL_LIBRARY.map(document => document.category))];
  const statuses = ["Tất cả", ...new Set(LEGAL_LIBRARY.map(document => document.status))];
  const years = [
    "Tất cả",
    ...new Set(LEGAL_LIBRARY.map(document => String(document.year)))
  ];

  const filtered = LEGAL_LIBRARY.filter(d =>
    (search === "" || d.name.toLowerCase().includes(search.toLowerCase())) &&
    (category === "Tất cả" || d.category === category) &&
    (status === "Tất cả" || d.status === status) &&
    (year === "Tất cả" || d.year.toString() === year)
  );

  if (selectedLaw) {
    return (
      <LawDetailView
        law={selectedLaw}
        onBack={() => setSelectedLaw(null)}
        onSelectLaw={setSelectedLaw}
        onGoToTree={() => {
          const document = MY_DOCUMENTS.find(candidate => candidate.id === selectedLaw.documentId);
          if (document) onSelectDocument(document);
          onNavigate("processing");
        }}
      />
    );
  }

  return (
    <div onClick={() => setOpenDrop(null)}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-bold text-gray-900">Thư viện pháp luật</h2>
          <p className="text-sm text-gray-500 mt-0.5">{filtered.length} văn bản</p>
        </div>
      </div>
      <div className="bg-white border border-black/[0.05] rounded-2xl p-4 mb-5 flex items-center gap-3 flex-wrap shadow-sm">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input value={search} onChange={e => { e.stopPropagation(); setSearch(e.target.value); }}
            onClick={e => e.stopPropagation()}
            placeholder="Tìm kiếm văn bản pháp luật..."
            className="w-full pl-8 pr-3 py-2 text-xs border border-gray-200 rounded-xl bg-gray-50/70 focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A]" />
        </div>
        <div className="flex gap-2 flex-wrap">
          <LibDropBtn label="Danh mục" value={category} opts={cats} openKey="cat" activeKey={openDrop} onOpen={setOpenDrop} onChange={setCategory} />
          <LibDropBtn label="Hiệu lực" value={status} opts={statuses} openKey="sta" activeKey={openDrop} onOpen={setOpenDrop} onChange={setStatus} />
          <LibDropBtn label="Năm ban hành" value={year} opts={years} openKey="yr" activeKey={openDrop} onOpen={setOpenDrop} onChange={setYear} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        {filtered.map(doc => (
          <div key={doc.id}
            onClick={e => { e.stopPropagation(); setSelectedLaw(doc); }}
            className="bg-white border border-black/[0.05] rounded-xl p-5 hover:shadow-lg hover:border-[#C41E3A]/15 transition-all cursor-pointer group">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 bg-[#0F1623] group-hover:bg-[#C41E3A] rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm transition-colors duration-200">
                <Scale className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-start gap-2 mb-1.5">
                  <h4 className="text-sm font-bold text-gray-900 line-clamp-2 flex-1">{doc.name}</h4>
                  <StatusPill status={doc.status} />
                </div>
                <div className="flex items-center gap-1.5 text-[10px] text-gray-400 mb-2">
                  <span className="font-mono font-semibold text-gray-600">{doc.number}</span>
                  <span>·</span><span>{doc.issuer}</span><span>·</span><span>{doc.year}</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full font-semibold">{doc.category}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── KNOWLEDGE NOTEBOOK ───────────────────────────────────────────────────────

function KnowledgeNotebookScreen() {
  const [search, setSearch] = useState("");
  const [activeCat, setActiveCat] = useState("Tất cả");
  const [docViewerTerm, setDocViewerTerm] = useState<string | null>(null);

  const cats = ["Tất cả", ...new Set(KNOWLEDGE_TERMS.map(term => term.category))];
  const filtered = KNOWLEDGE_TERMS.filter(t =>
    (search === "" || t.term.toLowerCase().includes(search.toLowerCase()) || t.definition.toLowerCase().includes(search.toLowerCase())) &&
    (activeCat === "Tất cả" || t.category === activeCat)
  );

  return (
    <>
      <div>
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Sổ tay kiến thức</h2>
            <p className="text-sm text-gray-500 mt-0.5">{filtered.length} mục từ pháp lý</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2.5 bg-[#C41E3A] hover:bg-[#a8172f] text-white rounded-xl text-xs font-bold transition-colors shadow-sm">
            <Plus className="w-3.5 h-3.5" />Thêm mục từ
          </button>
        </div>
        <div className="flex items-center gap-3 mb-5 flex-wrap">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Tìm kiếm..."
              className="pl-8 pr-4 py-2 text-xs border border-gray-200 rounded-xl bg-white w-52 focus:outline-none focus:ring-2 focus:ring-[#C41E3A]/20 focus:border-[#C41E3A] shadow-sm" />
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {cats.map(cat => (
              <button key={cat} onClick={() => setActiveCat(cat)}
                className={`px-3 py-1.5 text-[11px] rounded-full font-semibold transition-all ${activeCat === cat ? "bg-[#C41E3A] text-white shadow-sm" : "bg-white text-gray-600 border border-gray-200 hover:border-gray-300"}`}>
                {cat}
              </button>
            ))}
          </div>
        </div>
        <div className="bg-white border border-black/[0.05] rounded-2xl overflow-hidden shadow-sm">
          <div className="grid gap-0 text-[10px] font-bold text-gray-400 uppercase tracking-widest px-6 py-3 border-b border-gray-100 bg-gray-50/80"
            style={{ gridTemplateColumns: "32px 160px 1fr 160px" }}>
            <span>#</span><span>Thuật ngữ</span><span>Định nghĩa</span><span className="text-right">Nguồn</span>
          </div>
          {filtered.map((term, i) => (
            <div key={term.id} className="grid items-start gap-0 px-6 py-4 border-b border-gray-50 hover:bg-gray-50/60 transition-colors group"
              style={{ gridTemplateColumns: "32px 160px 1fr 160px" }}>
              <span className="text-[11px] text-gray-300 font-mono pt-0.5">{String(i + 1).padStart(2, "0")}</span>
              <div className="pr-5">
                <span className="text-sm font-bold text-gray-900 group-hover:text-[#C41E3A] transition-colors cursor-pointer">{term.term}</span>
                <div className="mt-1.5"><span className="text-[9px] px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full font-semibold uppercase tracking-wide">{term.category}</span></div>
              </div>
              <p className="text-xs text-gray-600 leading-relaxed pr-5">{term.definition}</p>
              <div className="text-right">
                <button
                  onClick={() => setDocViewerTerm(term.highlightTerm)}
                  className="text-[10px] px-2.5 py-1 bg-[#0F1623]/6 hover:bg-[#C41E3A] hover:text-white text-[#0F1623] rounded-full font-semibold whitespace-nowrap transition-all group/src"
                  title="Xem vị trí trong văn bản gốc">
                  {term.source}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* DocumentViewerModal opened when clicking source */}
      {docViewerTerm !== null && (
        <DocumentViewerModal
          onClose={() => setDocViewerTerm(null)}
          initialTerm={docViewerTerm}
        />
      )}
    </>
  );
}

// ─── PROCESSING ───────────────────────────────────────────────────────────────

function ProcessingScreen({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState(0);
  const stages = ["Đang đọc và phân tích tệp...", "Nhận diện cấu trúc văn bản...", "Trích xuất dữ liệu hành chính...", "Xây dựng sơ đồ tư duy...", "Phân tích hoàn tất!"];

  useEffect(() => {
    const timer = setInterval(() => {
      setProgress(p => {
        const next = Math.min(100, p + 1.8);
        setStage(Math.min(4, Math.floor(next / 20)));
        if (next >= 100) { clearInterval(timer); setTimeout(onComplete, 900); }
        return next;
      });
    }, 55);
    return () => clearInterval(timer);
  }, [onComplete]);

  return (
    <div className="fixed inset-0 bg-[#0A0F1A] flex items-center justify-center z-50">
      <div className="text-center w-full max-w-sm px-8">
        <div className="relative inline-flex items-center justify-center w-28 h-28 mb-8">
          <div className="absolute inset-0 rounded-full border-2 border-[#C41E3A]/20 animate-ping" style={{ animationDuration: "2s" }} />
          <div className="absolute inset-3 rounded-full border border-[#C41E3A]/15 animate-pulse" />
          <div className="w-20 h-20 bg-gradient-to-br from-[#C41E3A] to-[#8a1224] rounded-2xl flex items-center justify-center shadow-xl shadow-[#C41E3A]/30">
            <Brain className="w-9 h-9 text-white" />
          </div>
        </div>
        <div className="text-[10px] uppercase tracking-widest text-white/30 mb-2 font-semibold">VADS AI Analysis Engine</div>
        <h2 className="text-white text-xl font-bold mb-1.5" style={{ fontFamily: "'Playfair Display', serif" }}>Đang phân tích tài liệu</h2>
        <p className="text-white/40 text-sm mb-8">NĐ 15/2021/NĐ-CP · 48 trang · PDF</p>
        <div className="mb-2.5">
          <div className="h-1 bg-white/10 rounded-full overflow-hidden">
            <div className="h-full bg-gradient-to-r from-[#C41E3A] to-[#e0304e] rounded-full transition-all duration-200" style={{ width: `${progress}%` }} />
          </div>
        </div>
        <div className="flex items-center justify-between text-[11px] text-white/35 mb-8">
          <span>{stages[stage]}</span>
          <span className="font-mono font-semibold text-white/50">{Math.round(progress)}%</span>
        </div>
        <div className="flex justify-center gap-2">
          {stages.slice(0, 4).map((_, i) => (
            <div key={i} className={`rounded-full transition-all duration-300 ${i < stage ? "w-5 h-1.5 bg-[#C41E3A]" : i === stage ? "w-5 h-1.5 bg-[#C41E3A]/60 animate-pulse" : "w-1.5 h-1.5 bg-white/15"}`} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── TREE DIAGRAM ─────────────────────────────────────────────────────────────

function TreeDiagram({ onSelect, selectedId }: {
  onSelect: (n: DocNode) => void;
  selectedId: string | null;
}) {
  const root = TREE_DATA;
  const chapters = root.children ?? [];

  // Root node: black, clicking opens full document modal
  function RootNode() {
    const isSelected = selectedId === root.id;
    return (
      <button
        onMouseDown={e => e.stopPropagation()}
        onClick={e => { e.stopPropagation(); onSelect(root); }}
        className={`px-7 py-3.5 rounded-2xl bg-[#0F1623] text-white text-sm font-bold shadow-xl cursor-pointer transition-all hover:bg-[#1a2535] hover:scale-105 select-none ${isSelected ? "ring-2 ring-[#C41E3A] ring-offset-2" : ""}`}
      >
        <div className="text-white/50 text-[10px] uppercase tracking-widest mb-0.5 font-semibold">Nghị định</div>
        {root.label}
      </button>
    );
  }

  // White chapter nodes: show summary tooltip on click
  function ChapterNode({ ch }: { ch: DocNode }) {
    const isSelected = selectedId === ch.id;
    return (
      <button
        onMouseDown={e => e.stopPropagation()}
        onClick={e => { e.stopPropagation(); onSelect(ch); }}
        className={`px-4 py-3 bg-white border-2 rounded-xl text-xs font-bold text-[#0F1623] text-center min-w-[120px] whitespace-pre-line leading-snug shadow-sm cursor-pointer transition-all hover:shadow-md select-none ${isSelected ? "border-[#C41E3A] ring-2 ring-[#C41E3A]/30 shadow-md" : "border-gray-200 hover:border-[#C41E3A]/60"}`}
      >
        {ch.label}
      </button>
    );
  }

  // White article nodes: show summary tooltip on click
  function ArticleNode({ art }: { art: DocNode }) {
    const isSelected = selectedId === art.id;
    return (
      <button
        onMouseDown={e => e.stopPropagation()}
        onClick={e => { e.stopPropagation(); onSelect(art); }}
        className={`flex items-center gap-1.5 px-3 py-2 bg-white border rounded-xl text-xs shadow-sm cursor-pointer transition-all hover:shadow-md select-none ${isSelected ? "border-[#C41E3A] text-[#C41E3A] font-bold" : "border-gray-200 text-gray-700 hover:border-[#C41E3A]/40 hover:text-[#C41E3A]"}`}
      >
        <FileText className="w-3 h-3 flex-shrink-0" />
        {art.label}
      </button>
    );
  }

  const VLine = ({ h = 24 }: { h?: number }) => (
    <div className="w-px bg-gray-300 mx-auto" style={{ height: h }} />
  );

  return (
    <div className="flex flex-col items-center py-8 min-w-max">
      <RootNode />
      <VLine h={28} />
      <div className="relative flex items-start gap-10">
        {chapters.length > 1 && (
          <div className="absolute top-0 left-[60px] right-[60px] h-px bg-gray-300" />
        )}
        {chapters.map(ch => (
          <div key={ch.id} className="flex flex-col items-center">
            <VLine h={28} />
            <ChapterNode ch={ch} />
            <VLine h={20} />
            <div className="flex flex-col gap-2 items-start">
              {ch.children?.map(art => <ArticleNode key={art.id} art={art} />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── WHITEBOARD SCREEN ────────────────────────────────────────────────────────

function WhiteboardScreen({ onNavigate, importData, onProfile, onImport }: { onNavigate: (s: Screen) => void; importData: ImportData | null; onProfile: () => void; onImport: () => void }) {
  const [zoom, setZoom] = useState(0.9);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [selected, setSelected] = useState<DocNode | null>(null);
  const [showShare, setShowShare] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState(INIT_CHAT);
  const [showDocViewer, setShowDocViewer] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [showSummary, setShowSummary] = useState(true);
  const [splitRatio, setSplitRatio] = useState(0.68);
  const [activeSection, setActiveSection] = useState<string | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef(zoom);
  const panRef = useRef(pan);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const splitContainerRef = useRef<HTMLDivElement>(null);
  const isDraggingSplit = useRef(false);
  const rightPanelRef = useRef<HTMLDivElement>(null);
  const panInitialized = useRef(false);
  const sRef0 = useRef<HTMLDivElement>(null);
  const sRef1 = useRef<HTMLDivElement>(null);
  const sRef2 = useRef<HTMLDivElement>(null);
  const sRef3 = useRef<HTMLDivElement>(null);

  const sectionDocMap: Record<string, React.RefObject<HTMLDivElement>> = {
    thucTrang: sRef0, mucTieu: sRef1, noiDung: sRef2, phuongAn: sRef3,
  };

  useEffect(() => { zoomRef.current = zoom; }, [zoom]);
  useEffect(() => { panRef.current = pan; }, [pan]);

  useEffect(() => {
    if (!showSummary && canvasRef.current && !panInitialized.current) {
      panInitialized.current = true;
      const rect = canvasRef.current.getBoundingClientRect();
      setPan({ x: rect.width / 2 - 380, y: rect.height / 2 - 220 });
    }
  }, [showSummary]);

  // Split panel drag
  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      if (!isDraggingSplit.current || !splitContainerRef.current) return;
      const rect = splitContainerRef.current.getBoundingClientRect();
      setSplitRatio(Math.max(0.4, Math.min(0.82, (e.clientX - rect.left) / rect.width)));
    };
    const handleUp = () => {
      isDraggingSplit.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    document.addEventListener("mousemove", handleMove);
    document.addEventListener("mouseup", handleUp);
    return () => { document.removeEventListener("mousemove", handleMove); document.removeEventListener("mouseup", handleUp); };
  }, []);

  useEffect(() => {
    if (showSummary) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const handler = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      const factor = e.deltaY < 0 ? 1.08 : 0.93;
      const currentZoom = zoomRef.current;
      const currentPan = panRef.current;
      const newZoom = Math.min(4, Math.max(0.15, currentZoom * factor));
      const ratio = newZoom / currentZoom;
      setZoom(newZoom);
      setPan({ x: cx + (currentPan.x - cx) * ratio, y: cy + (currentPan.y - cy) * ratio });
    };
    canvas.addEventListener("wheel", handler, { passive: false });
    return () => canvas.removeEventListener("wheel", handler);
  }, [showSummary]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
    setPanStart({ ...panRef.current });
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: panStart.x + (e.clientX - dragStart.x), y: panStart.y + (e.clientY - dragStart.y) });
  };
  const handleMouseUp = () => setIsDragging(false);

  // Root node → open document viewer; white nodes → show summary tooltip
  const handleNodeSelect = (node: DocNode) => {
    if (node.type === "root") {
      setShowDocViewer(true);
      setSelected(null);
      return;
    }
    setSelected(prev => prev?.id === node.id ? null : node);
  };

  const handleSend = () => {
    if (!chatInput.trim()) return;
    const q = chatInput;
    setMessages(prev => [...prev, { role: "user", text: q }]);
    setChatInput("");
    if (!ACTIVE_DOCUMENT_ID) {
      setMessages(prev => [...prev, { role: "assistant", text: "Vui lòng chọn một tài liệu trước khi đặt câu hỏi." }]);
      return;
    }
    void askLegacyDocument(ACTIVE_DOCUMENT_ID, q)
      .then(text => setMessages(prev => [...prev, { role: "assistant", text }]))
      .catch(reason => setMessages(prev => [...prev, {
        role: "assistant",
        text: reason instanceof Error ? reason.message : "Không thể truy vấn tài liệu.",
      }]));
  };

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const scrollToDocSection = (key: string) => {
    setActiveSection(key);
    const ref = sectionDocMap[key];
    if (ref?.current && rightPanelRef.current) {
      const panelTop = rightPanelRef.current.getBoundingClientRect().top;
      const elemTop = ref.current.getBoundingClientRect().top;
      rightPanelRef.current.scrollTop += elemTop - panelTop - 16;
    }
  };

  const user = importData ?? { ten: "Nguyễn Văn An", chucVu: "Chuyên viên pháp chế", phongBan: "Phòng Pháp chế", thon: "", xa: "Xã Phú Xuân", tinh: "Tỉnh Thái Bình", baoCaoFile: null, vanBanFile: null };

  const ANALYSIS_SECTIONS = [
    {
      key: "thucTrang", icon: Layers, color: "text-blue-600", bg: "bg-blue-50", activeBorder: "border-blue-400",
      title: "Thực trạng",
      subtitle: `Dựa trên Báo cáo thực trạng${user.baoCaoFile ? ` — ${user.baoCaoFile}` : ""}`,
      content: `${user.tinh} hiện có 47 dự án đầu tư xây dựng đang triển khai, trong đó 23 dự án sử dụng vốn đầu tư công. Tình trạng chậm tiến độ xảy ra ở 38% dự án, chủ yếu do:\n\n• Phân cấp thẩm quyền quyết định đầu tư còn chồng chéo giữa UBND xã và huyện\n• Thiếu cán bộ kỹ thuật chuyên ngành tại cấp ${user.xa || "xã"}\n• Quy trình nghiệm thu, bàn giao còn kéo dài do thiếu nhân lực kiểm tra\n• 12 dự án nhóm B cần làm rõ thẩm quyền phê duyệt theo quy định mới`,
    },
    {
      key: "mucTieu", icon: CheckCircle2, color: "text-emerald-600", bg: "bg-emerald-50", activeBorder: "border-emerald-400",
      title: "Mục tiêu",
      subtitle: `Từ văn bản hành chính${user.vanBanFile ? ` — ${user.vanBanFile}` : " — NĐ 15/2021/NĐ-CP"}`,
      content: `Nghị định 15/2021/NĐ-CP hướng đến:\n\n• Nâng cao hiệu quả quản lý nhà nước về đầu tư xây dựng sử dụng vốn công\n• Phân định rõ trách nhiệm giữa chủ đầu tư, ban QLDA và các bên liên quan\n• Rút ngắn thủ tục hành chính 30–40% so với Nghị định 59/2015\n• Tăng cường phân cấp cho địa phương (UBND cấp tỉnh, huyện) trong phê duyệt dự án nhóm B, C\n• Đảm bảo minh bạch trong đấu thầu và nghiệm thu công trình`,
    },
    {
      key: "noiDung", icon: FileText, color: "text-violet-600", bg: "bg-violet-50", activeBorder: "border-violet-400",
      title: "Nội dung chính của văn bản hành chính",
      subtitle: "Tóm tắt các điều khoản trọng yếu",
      content: `Nghị định gồm 3 chương, 10 điều với các nội dung cốt lõi:\n\n1. Phân loại dự án (Điều 4): Nhóm A ≥2.300 tỷ, Nhóm B 120–2.300 tỷ, Nhóm C <120 tỷ\n2. Thẩm quyền phê duyệt (Điều 5): Quốc hội → Thủ tướng → UBND tỉnh theo từng nhóm\n3. Hình thức ban QLDA (Điều 8): 3 hình thức — chuyên ngành, khu vực, hoặc thuê tư vấn\n4. Giám sát & nghiệm thu (Điều 9, 10): Quy trình kiểm tra chất lượng và bàn giao\n5. Điều chỉnh dự án (Điều 7): Cho phép điều chỉnh khi vượt 10% tổng mức đầu tư`,
    },
    {
      key: "phuongAn", icon: Lightbulb, color: "text-amber-600", bg: "bg-amber-50", activeBorder: "border-amber-400",
      title: "Phương án đề xuất",
      subtitle: `Cho ${user.chucVu} — ${user.phongBan}`,
      content: `Dựa trên thực trạng ${user.tinh} và quy định mới tại NĐ 15/2021:\n\n🔴 Ưu tiên cao:\n• Rà soát lại toàn bộ 12 dự án nhóm B về thẩm quyền phê duyệt — cần ý kiến pháp lý trước 31/12\n• Soạn thảo quy trình nội bộ mới cho ${user.phongBan} phù hợp Điều 8 (hình thức ban QLDA)\n\n🟡 Trung hạn:\n• Đề xuất bổ sung 2 cán bộ kỹ thuật tại cấp xã để đáp ứng yêu cầu giám sát Điều 9\n• Xây dựng mẫu hồ sơ nghiệm thu theo quy định mới của Điều 10\n\n🟢 Tác động tích cực:\n• Dự kiến rút ngắn thời gian phê duyệt dự án nhóm C xuống còn 15 ngày làm việc\n• Giảm chi phí quản lý dự án 15–20% nhờ phân cấp thẩm quyền`,
    },
  ];

  const docSectionRefMap: Record<string, React.RefObject<HTMLDivElement>> = {
    preamble: sRef0, "dieu-1": sRef1, "chuong-2": sRef2, "chuong-3": sRef3,
  };

  const SIDEBAR_W = 64;

  return (
    <div className="fixed inset-0 overflow-hidden" style={{ background: "#F0F1F3" }}>
      {/* ── Sidebar (collapsed, same as main app) ── */}
      <Sidebar active="tree" onNavigate={onNavigate} collapsed={true} onToggle={() => {}} onProfile={onProfile} onImport={onImport} />

      {/* ── Top bar ── */}
      <div className="fixed top-0 right-0 h-14 bg-white border-b border-black/[0.06] flex items-center pr-5 z-20 shadow-sm" style={{ left: SIDEBAR_W }}>
        <div className="flex items-center gap-2 flex-1 pl-6 min-w-0">
          <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          <span className="text-sm font-bold text-gray-900 truncate">Phân tích tài liệu</span>
          <span className="text-gray-300 mx-1">·</span>
          <span className="text-xs text-gray-500 truncate">{user.vanBanFile ?? "NĐ 15/2021/NĐ-CP"}</span>
        </div>
        <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-lg transition-colors mr-1">
          <Download className="w-3.5 h-3.5" />Xuất báo cáo
        </button>
        <button onClick={() => setShowShare(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[#C41E3A] hover:bg-[#a8172f] text-white text-xs font-bold rounded-lg transition-colors shadow-sm">
          <Share2 className="w-3.5 h-3.5" />Chia sẻ
        </button>
      </div>

      {/* ── Main content ── */}
      <div className="absolute bottom-0 right-0 overflow-hidden" style={{ top: 56, left: SIDEBAR_W }}>
        {showSummary ? (
          /* ── Summary: resizable 7-3 split ── */
          <div ref={splitContainerRef} className="h-full flex overflow-hidden">
            {/* Left panel — analysis sections */}
            <div className="overflow-y-auto" style={{ width: `${splitRatio * 100}%`, background: "#F0F1F3" }}>
              <div className="p-5 space-y-4">
                <div className="flex items-center gap-3 mb-1">
                  <div className="w-8 h-8 bg-[#C41E3A] rounded-xl flex items-center justify-center shadow-sm flex-shrink-0">
                    <Brain className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-gray-900">Tóm tắt tài liệu — AI Generated</h2>
                    <p className="text-[10px] text-gray-400">{user.chucVu} · {user.phongBan} · {user.tinh}</p>
                  </div>
                </div>

                {ANALYSIS_SECTIONS.map(({ key, icon: Icon, color, bg, activeBorder, title, subtitle, content }) => {
                  const isActive = activeSection === key;
                  return (
                    <div key={key} onClick={() => scrollToDocSection(key)}
                      className={`bg-white rounded-2xl shadow-sm border cursor-pointer transition-all hover:shadow-md ${isActive ? `${activeBorder} border-2` : "border-gray-100 hover:border-gray-200"}`}>
                      <div className="p-4">
                        <div className="flex items-start gap-3">
                          <div className={`w-7 h-7 ${bg} rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5`}>
                            <Icon className={`w-3.5 h-3.5 ${color}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <h3 className="text-sm font-bold text-gray-900">{title}</h3>
                              {isActive && (
                                <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${bg} ${color}`}>Đang xem</span>
                              )}
                            </div>
                            <p className="text-[10px] text-gray-400 mb-3">{subtitle}</p>
                            <div className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">{content}</div>
                          </div>
                        </div>
                      </div>
                      <div className="border-t border-gray-50 px-4 py-2 flex items-center gap-1.5">
                        <span className="text-[10px] text-gray-400">Nhấp để xem trong văn bản gốc</span>
                        <ChevronRight className="w-3 h-3 text-gray-300" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Drag handle */}
            <div
              className="w-1.5 flex-shrink-0 bg-gray-200 hover:bg-[#C41E3A]/60 transition-colors cursor-col-resize flex items-center justify-center group"
              onMouseDown={() => { isDraggingSplit.current = true; document.body.style.cursor = "col-resize"; document.body.style.userSelect = "none"; }}
            >
              <div className="w-5 h-10 flex items-center justify-center rounded-full bg-gray-300 group-hover:bg-[#C41E3A] transition-colors">
                <GripVertical className="w-3 h-3 text-white" />
              </div>
            </div>

            {/* Right panel — original document */}
            <div ref={rightPanelRef} className="flex-1 overflow-y-auto bg-white">
              <div className="sticky top-0 bg-white border-b border-gray-100 px-4 py-2.5 flex items-center gap-2 z-10 shadow-sm">
                <Eye className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-xs font-semibold text-gray-700">Văn bản gốc</span>
                <span className="ml-auto text-[10px] text-gray-400 truncate max-w-[140px]">{user.vanBanFile ?? "NĐ 15/2021/NĐ-CP"}</span>
              </div>
              <div className="p-5 text-xs text-gray-800 leading-relaxed space-y-4" style={{ fontFamily: "Georgia, 'Times New Roman', serif" }}>
                {DOCUMENT_SECTIONS.map(sec => {
                  const ref = docSectionRefMap[sec.id];
                  return (
                    <div key={sec.id} ref={ref}>
                      {sec.heading && (
                        <h3 className={`font-bold mb-2 ${sec.id.startsWith("chuong") ? "text-[13px] text-[#0F1623] mt-6 pb-1.5 border-b border-gray-100" : "text-[12px] text-gray-900"}`}>
                          {sec.heading}
                        </h3>
                      )}
                      {sec.content && (
                        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{sec.content}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          /* ── Tree diagram canvas ── */
          <>
            <div ref={canvasRef} className="absolute inset-0 overflow-hidden"
              style={{ cursor: isDragging ? "grabbing" : "grab" }}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}>
              <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ opacity: 0.3 }}>
                <defs>
                  <pattern id="dots2" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
                    <circle cx="1" cy="1" r="1" fill="#9CA3AF" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#dots2)" />
              </svg>
              <div style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: "0 0" }}>
                <TreeDiagram onSelect={handleNodeSelect} selectedId={selected?.id ?? null} />
              </div>

              {selected && selected.type !== "root" && (
                <div className="absolute bottom-20 left-1/2 -translate-x-1/2 w-80 bg-white rounded-2xl shadow-2xl shadow-black/15 border border-gray-200 p-4 z-20"
                  onMouseDown={e => e.stopPropagation()}>
                  <div className="flex items-start justify-between gap-2 mb-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-gray-100 rounded-md flex items-center justify-center">
                        <GitBranch className="w-3 h-3 text-gray-500" />
                      </div>
                      <span className="text-sm font-bold text-gray-900">{selected.label.replace("\n", " — ")}</span>
                    </div>
                    <button onClick={() => setSelected(null)} className="text-gray-300 hover:text-gray-500 p-0.5 rounded"><X className="w-3.5 h-3.5" /></button>
                  </div>
                  <p className="text-xs text-gray-600 leading-relaxed mb-3">{selected.summary}</p>
                  <button onMouseDown={e => e.stopPropagation()} onClick={() => setShowDetail(true)}
                    className="w-full bg-[#0F1623] hover:bg-[#1a2535] text-white text-xs py-2.5 rounded-xl font-bold flex items-center justify-center gap-1.5 shadow-sm transition-colors">
                    Xem chi tiết <ExternalLink className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>

            {/* Zoom controls */}
            <div className="absolute top-4 right-4 flex items-center gap-1.5 bg-white rounded-xl shadow-lg border border-gray-200 p-1.5 z-30">
              <button onClick={() => setZoom(z => Math.max(0.15, z * 0.85))} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-600 transition-colors"><ZoomOut className="w-3.5 h-3.5" /></button>
              <span className="text-[11px] font-mono font-semibold text-gray-700 w-12 text-center">{Math.round(zoom * 100)}%</span>
              <button onClick={() => setZoom(z => Math.min(4, z * 1.18))} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-600 transition-colors"><ZoomIn className="w-3.5 h-3.5" /></button>
              <div className="w-px h-4 bg-gray-200" />
              <button onClick={() => { setZoom(0.9); if (canvasRef.current) { const r = canvasRef.current.getBoundingClientRect(); setPan({ x: r.width / 2 - 380, y: r.height / 2 - 220 }); } }}
                className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-600 transition-colors"><Maximize2 className="w-3.5 h-3.5" /></button>
            </div>
          </>
        )}

        {/* FAB toggle */}
        <button
          onClick={() => setShowSummary(v => !v)}
          className="absolute bottom-6 right-6 z-30 flex items-center gap-2.5 text-white px-6 py-3.5 rounded-full shadow-2xl transition-all hover:scale-105 active:scale-95 font-bold text-sm"
          style={{ background: showSummary ? "#0F1623" : "#C41E3A", boxShadow: showSummary ? "0 8px 24px rgba(15,22,35,0.35)" : "0 8px 24px rgba(196,30,58,0.35)" }}
        >
          {showSummary ? <GitBranch className="w-4 h-4" /> : <Brain className="w-4 h-4" />}
          {showSummary ? "Sơ đồ trực quan" : "Tóm tắt tài liệu"}
        </button>

        {/* AI Chat */}
        <div className="absolute bottom-6 left-6 z-30">
          {showChat ? (
            <div className="bg-white rounded-2xl shadow-2xl shadow-black/15 border border-gray-200 w-72 overflow-hidden">
              <div className="bg-[#0F1623] px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <div className="w-6 h-6 bg-[#C41E3A] rounded-full flex items-center justify-center"><Brain className="w-3 h-3 text-white" /></div>
                    <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-emerald-400 rounded-full animate-ping" style={{ animationDuration: "1.5s" }} />
                    <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-emerald-400 rounded-full" />
                  </div>
                  <span className="text-white text-xs font-bold">Trợ lí AI VADS</span>
                </div>
                <button onClick={() => setShowChat(false)} className="text-white/40 hover:text-white/80 p-0.5 rounded"><X className="w-3.5 h-3.5" /></button>
              </div>
              <div className="h-56 overflow-y-auto p-3 space-y-2 bg-gray-50/60">
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[88%] px-3 py-2 rounded-xl text-[11px] leading-relaxed ${msg.role === "user" ? "bg-[#C41E3A] text-white rounded-br-sm" : "bg-white text-gray-700 border border-gray-100 shadow-sm rounded-bl-sm"}`}>
                      {msg.text}
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              <div className="border-t border-gray-100 p-2.5 flex gap-2 bg-white">
                <input value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSend()}
                  placeholder="Hỏi về nội dung tài liệu..."
                  className="flex-1 px-3 py-1.5 text-[11px] bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:border-[#C41E3A] transition-colors" />
                <button onClick={handleSend} className="p-2 bg-[#C41E3A] rounded-lg text-white hover:bg-[#a8172f] transition-colors flex-shrink-0"><Send className="w-3 h-3" /></button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowChat(true)}
              className="relative flex items-center gap-2.5 bg-[#C41E3A] hover:bg-[#a8172f] text-white px-4 py-2.5 rounded-full shadow-lg shadow-[#C41E3A]/30 transition-all hover:scale-105">
              <div className="absolute inset-0 rounded-full bg-[#C41E3A] animate-ping opacity-25" style={{ animationDuration: "2s" }} />
              <div className="relative">
                <Brain className="w-4 h-4 text-white" />
                <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDuration: "1s" }} />
              </div>
              <span className="text-xs font-bold relative">Chat với trợ lí AI</span>
            </button>
          )}
        </div>
      </div>

      {showShare && <ShareModal onClose={() => setShowShare(false)} />}
      {showDocViewer && <DocumentViewerModal onClose={() => setShowDocViewer(false)} />}
      {showDetail && <DetailModal onClose={() => setShowDetail(false)} />}
    </div>
  );
}

// ─── DETAIL MODAL ─────────────────────────────────────────────────────────────

function DetailModal({ onClose }: { onClose: () => void }) {
  const ADMIN_ROWS = [
    { field: "Cơ quan ban hành", value: "Chính phủ nước CHXHCN Việt Nam", warn: false },
    { field: "Số hiệu văn bản", value: "15/2021/NĐ-CP", warn: false },
    { field: "Ngày ban hành", value: "03/03/2021", warn: false },
    { field: "Đơn vị chủ trì", value: "—", warn: true },
    { field: "Ngân sách thực hiện", value: "Chưa xác định", warn: true },
    { field: "Thời hạn hiệu lực", value: "Không quy định thời hạn", warn: false },
    { field: "Ký bởi", value: "Thủ tướng Nguyễn Xuân Phúc", warn: false },
  ];
  const RELATED = [
    { name: "Nghị định 59/2015/NĐ-CP (văn bản bị thay thế)", status: "Hết hiệu lực" },
    { name: "Luật Xây dựng 2014 sửa đổi, bổ sung 2020", status: "Còn hiệu lực" },
    { name: "Thông tư 09/2021/TT-BXD hướng dẫn thi hành NĐ 15", status: "Còn hiệu lực" },
    { name: "Luật Đầu tư công 2019 (số 39/2019/QH14)", status: "Còn hiệu lực" },
  ];

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-6">
      <div className="bg-white rounded-2xl w-full max-w-5xl flex flex-col shadow-2xl border border-gray-200" style={{ height: "85vh" }}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[#0F1623] rounded-xl flex items-center justify-center shadow-sm"><FileText className="w-4 h-4 text-white" /></div>
            <div>
              <h2 className="text-sm font-bold text-gray-900">NĐ 15/2021/NĐ-CP — Phân tích chi tiết</h2>
              <p className="text-[10px] text-gray-400 mt-0.5">Phân tích bởi VADS AI · 03/03/2021 · 48 trang</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"><X className="w-5 h-5" /></button>
        </div>
        <div className="flex flex-1 overflow-hidden">
          <div className="border-r border-gray-100 overflow-y-auto p-6 space-y-5" style={{ width: "60%" }}>
            <section>
              <div className="flex items-center gap-2 mb-3"><div className="w-5 h-5 bg-[#C41E3A]/10 rounded flex items-center justify-center"><Brain className="w-3 h-3 text-[#C41E3A]" /></div><h3 className="text-xs font-bold text-gray-800 uppercase tracking-wide">Tóm tắt thông minh</h3></div>
              <SummaryTabs />
            </section>
            <section className="space-y-2">
              <div className="flex items-start gap-3 p-3.5 bg-amber-50 border border-amber-200 rounded-xl">
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <div><p className="text-xs font-bold text-amber-800">Chưa có đơn vị chủ trì</p><p className="text-[11px] text-amber-700 mt-0.5 leading-relaxed">Nghị định không chỉ định cụ thể đơn vị chủ trì triển khai. Cần bổ sung trong văn bản hướng dẫn.</p></div>
              </div>
              <div className="flex items-start gap-3 p-3.5 bg-red-50 border border-red-200 rounded-xl">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <div><p className="text-xs font-bold text-red-800">Số liệu mâu thuẫn</p><p className="text-[11px] text-red-700 mt-0.5 leading-relaxed">Điều 4 và Điều 7 có quy định mâu thuẫn về ngưỡng tổng mức đầu tư nhóm B.</p></div>
              </div>
            </section>
            <section>
              <div className="flex items-center gap-2 mb-3"><div className="w-5 h-5 bg-blue-50 rounded flex items-center justify-center"><Building2 className="w-3 h-3 text-blue-500" /></div><h3 className="text-xs font-bold text-gray-800 uppercase tracking-wide">Thông tin hành chính</h3></div>
              <div className="border border-gray-100 rounded-xl overflow-hidden">
                {ADMIN_ROWS.map((row, i) => (
                  <div key={i} className={`flex items-center ${i < ADMIN_ROWS.length - 1 ? "border-b border-gray-50" : ""}`}>
                    <div className="w-2/5 px-4 py-2.5 bg-gray-50/80 text-[11px] font-semibold text-gray-500">{row.field}</div>
                    <div className="flex-1 px-4 py-2.5 flex items-center justify-between gap-2">
                      <span className={`text-[11px] ${row.value === "—" || row.value.includes("Chưa") ? "text-gray-400 italic" : "text-gray-800 font-medium"}`}>{row.value}</span>
                      {row.warn && <AlertTriangle className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />}
                    </div>
                  </div>
                ))}
              </div>
            </section>
            <section>
              <div className="flex items-center gap-2 mb-3"><div className="w-5 h-5 bg-violet-50 rounded flex items-center justify-center"><Lightbulb className="w-3 h-3 text-violet-500" /></div><h3 className="text-xs font-bold text-gray-800 uppercase tracking-wide">Hỏi & Đáp tự động (AI)</h3></div>
              <div className="space-y-2.5">
                {[
                  { q: "Nghị định này áp dụng cho loại dự án nào?", a: "Áp dụng cho tất cả dự án đầu tư xây dựng sử dụng vốn đầu tư công và vốn nhà nước ngoài đầu tư công trên toàn lãnh thổ Việt Nam theo Điều 1." },
                  { q: "Dự án nhóm A có tổng mức đầu tư là bao nhiêu?", a: "Theo Điều 4, dự án nhóm A từ 2.300 tỷ đồng trở lên. Lưu ý: có mâu thuẫn với Điều 7 cần làm rõ." },
                ].map((qa, i) => (
                  <div key={i} className="bg-gray-50 rounded-xl p-3.5 border border-gray-100">
                    <p className="text-[11px] font-bold text-gray-800 mb-1.5 flex items-start gap-1.5"><span className="text-[#C41E3A] flex-shrink-0 mt-0.5">Q.</span>{qa.q}</p>
                    <p className="text-[11px] text-gray-600 leading-relaxed flex items-start gap-1.5"><span className="text-emerald-600 font-bold flex-shrink-0 mt-0.5">A.</span>{qa.a}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
          <div className="overflow-y-auto p-6 space-y-5" style={{ width: "40%" }}>
            <section>
              <div className="flex items-center gap-2 mb-3"><div className="w-5 h-5 bg-gray-100 rounded flex items-center justify-center"><Eye className="w-3 h-3 text-gray-500" /></div><h3 className="text-xs font-bold text-gray-800 uppercase tracking-wide">Văn bản gốc</h3></div>
              <div className="border border-gray-200 rounded-xl overflow-hidden">
                <div className="bg-gray-50 border-b border-gray-100 px-3 py-2 flex items-center justify-between">
                  <span className="text-[10px] text-gray-400 font-semibold">Trang 3 / 48 · Chương I</span>
                  <div className="flex gap-0.5">
                    <button className="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"><ChevronLeft className="w-3.5 h-3.5" /></button>
                    <button className="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100"><ChevronRight className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
                <div className="p-4 text-[11px] text-gray-800 leading-relaxed space-y-2.5 bg-white" style={{ fontFamily: "Georgia, serif" }}>
                  <p className="text-center font-bold text-xs">CHƯƠNG I</p>
                  <p className="text-center font-semibold text-[11px]">QUY ĐỊNH CHUNG</p>
                  <div><p className="font-bold mb-1">Điều 1. Phạm vi điều chỉnh</p><p className="text-gray-600">Nghị định này quy định về quản lý dự án đầu tư xây dựng, bao gồm: lập, thẩm định, phê duyệt dự án; thiết kế, dự toán xây dựng; lựa chọn nhà thầu; thi công xây dựng; nghiệm thu, bàn giao...</p></div>
                  <div className="bg-yellow-50 border-l-2 border-yellow-400 pl-3 py-1 rounded-r-lg"><p className="font-bold mb-1">Điều 2. Đối tượng áp dụng</p><p className="text-gray-600">Nghị định này áp dụng đối với <span className="bg-yellow-200 px-0.5 rounded font-medium">cơ quan, tổ chức, cá nhân</span> tham gia hoạt động quản lý dự án đầu tư xây dựng sử dụng vốn đầu tư công...</p></div>
                </div>
              </div>
            </section>
            <section>
              <div className="flex items-center gap-2 mb-3"><div className="w-5 h-5 bg-gray-100 rounded flex items-center justify-center"><Network className="w-3 h-3 text-gray-500" /></div><h3 className="text-xs font-bold text-gray-800 uppercase tracking-wide">Văn bản liên quan</h3></div>
              <div className="space-y-2">
                {RELATED.map((doc, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-gray-50 border border-gray-100 rounded-xl hover:bg-gray-100 cursor-pointer group transition-colors">
                    <Scale className="w-4 h-4 text-gray-300 flex-shrink-0 group-hover:text-[#C41E3A] transition-colors" />
                    <p className="text-[11px] text-gray-700 font-medium flex-1 leading-snug">{doc.name}</p>
                    <StatusPill status={doc.status} />
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── APP ─────────────────────────────────────────────────────────────────────

const TITLES: Record<Screen, string> = {
  login: "Login", dashboard: "Dashboard", documents: "Tài liệu của tôi",
  library: "Thư viện pháp luật", notebook: "Sổ tay kiến thức", processing: "Đang xử lý...", tree: "Phân tích tài liệu",
};

export default function UserPortal({ currentUser, onLogout }: { currentUser: UserPublic; onLogout: () => void }) {
  const [screen, setScreen] = useState<Screen>("dashboard");
  const [collapsed, setCollapsed] = useState(true);
  const [showProfile, setShowProfile] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [importData, setImportData] = useState<ImportData | null>(null);
  const [, setPortalDataVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      void loadLegacyPortalData()
        .then(data => {
          if (cancelled) return;
          MY_DOCUMENTS = data.documents;
          LEGAL_LIBRARY = data.laws;
          Object.assign(LAW_DETAILS, data.lawDetails);
          setPortalDataVersion(version => version + 1);
          void loadLegacyKnowledgeTerms(data.documents)
            .then(terms => {
              if (cancelled) return;
              KNOWLEDGE_TERMS = terms;
              setPortalDataVersion(version => version + 1);
            })
            .catch(reason => {
              if (!cancelled) {
                window.alert(reason instanceof Error ? reason.message : "KhÃ´ng thá»ƒ táº£i sá»• tay kiáº¿n thá»©c.");
              }
            });
        })
        .catch(reason => {
          if (!cancelled) {
            window.alert(reason instanceof Error ? reason.message : "Không thể tải dữ liệu hệ thống.");
          }
        });
    };
    refresh();
    window.addEventListener("vads:documents-changed", refresh);
    return () => {
      cancelled = true;
      window.removeEventListener("vads:documents-changed", refresh);
    };
  }, []);

  const navigate = (s: Screen) => setScreen(s);
  const handleImportSubmit = (data: ImportData) => { setImportData(data); setScreen("processing"); };
  const selectDocument = (document: LegacyDocument) => {
    ACTIVE_DOCUMENT_ID = document.id;
    TREE_DATA = {
      id: document.id,
      label: document.name,
      type: "root",
      summary: "Đang tải Knowledge Graph từ hệ thống...",
      children: [],
    };
    KNOWLEDGE_TERMS = [];
    setImportData(current => ({
      ten: current?.ten ?? currentUser.full_name,
      chucVu: current?.chucVu ?? "",
      phongBan: current?.phongBan ?? "",
      thon: current?.thon ?? "",
      xa: current?.xa ?? "",
      tinh: current?.tinh ?? "",
      baoCaoFile: current?.baoCaoFile ?? null,
      vanBanFile: document.name,
    }));
    void loadLegacyGraph(document)
      .then(({ tree, terms }) => {
        TREE_DATA = tree;
        KNOWLEDGE_TERMS = terms;
        setPortalDataVersion(version => version + 1);
      })
      .catch(reason => {
        TREE_DATA = {
          id: document.id,
          label: document.name,
          type: "root",
          summary: reason instanceof Error ? reason.message : "Không thể tạo Knowledge Graph.",
          children: [],
        };
        setPortalDataVersion(version => version + 1);
        window.alert(TREE_DATA.summary);
      });
  };

  if (screen === "tree") return (
    <>
      <WhiteboardScreen onNavigate={navigate} importData={importData} onProfile={() => setShowProfile(true)} onImport={() => setShowImport(true)} />
      {showProfile && <ProfileModal onClose={() => setShowProfile(false)} currentUser={currentUser} onChanged={onLogout} />}
      {showImport && <ImportModal onClose={() => setShowImport(false)} onSubmit={handleImportSubmit} currentUser={currentUser} />}
    </>
  );

  if (screen === "processing") return (
    <>
      <MainLayout active="dashboard" title="Đang xử lý tài liệu" onNavigate={navigate} collapsed={collapsed} onToggle={() => setCollapsed(v => !v)} onProfile={() => setShowProfile(true)} onImport={() => setShowImport(true)}>
        <div className="h-96 flex items-center justify-center"><p className="text-gray-400 text-sm">Đang phân tích...</p></div>
      </MainLayout>
      <ProcessingScreen onComplete={() => setScreen("tree")} />
    </>
  );

  return (
    <>
      <button onClick={onLogout} title={`Đăng xuất ${currentUser.full_name}`} className="fixed right-5 bottom-5 z-50 bg-[#0F1623] text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-xl hover:bg-black">Đăng xuất</button>
      <MainLayout active={screen} title={TITLES[screen]} onNavigate={navigate} collapsed={collapsed} onToggle={() => setCollapsed(v => !v)} onProfile={() => setShowProfile(true)} onImport={() => setShowImport(true)}>
        {screen === "dashboard" && <DashboardScreen onNavigate={navigate} onAnalyzeUploaded={() => {
          if (MY_DOCUMENTS[0]) selectDocument(MY_DOCUMENTS[0]);
        }} />}
        {screen === "documents" && <MyDocumentsScreen onNavigate={navigate} onSelectDocument={selectDocument} />}
        {screen === "library" && <LegalLibraryScreen onNavigate={navigate} onSelectDocument={selectDocument} />}
        {screen === "notebook" && <KnowledgeNotebookScreen />}
      </MainLayout>
      {showProfile && <ProfileModal onClose={() => setShowProfile(false)} currentUser={currentUser} onChanged={onLogout} />}
      {showImport && <ImportModal onClose={() => setShowImport(false)} onSubmit={handleImportSubmit} currentUser={currentUser} />}
    </>
  );
}
