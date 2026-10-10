"""Rebuild synthetic, nonpersonal fixtures and simple vector-drawn assets.

Run from any directory: python examples/build_examples.py
The figures describe fictional design targets, never measured project results.
"""

from __future__ import annotations

import json
from pathlib import Path

import fitz

BASE = Path(__file__).resolve().parent
DATA = BASE / "documents"


DOCUMENTS = [
    {"doc_id": "harbor", "title": "港湾资料借阅系统方案", "page_count": 3,
     "sections": [
         {"id": "s1", "title": "范围与服务", "page": 1, "text": "港湾资料借阅系统为资料室提供检索、借阅与归还管理。试点规模为2000名读者。服务时间为每日08:00至22:00。"},
         {"id": "s2", "title": "借阅规则", "page": 2, "text": "每名读者同时最多借阅3份资料。首次借阅期限为14天，允许续借1次，续借延长7天。资料存在其他读者预约时，不允许续借。"},
         {"id": "s3", "title": "权限与审计", "page": 2, "text": "系统包含读者和资料管理员两种角色。读者只能查询自己的借阅记录；资料管理员可以登记资料和处理归还。借阅操作审计日志保留180天。导出的统计结果不包含读者姓名。"},
         {"id": "s4", "title": "交付与恢复", "page": 3, "text": "试点建设周期为4周。验收要求借阅状态核对准确率不低于99%。出现服务故障后，应在15分钟内恢复服务。管理员在每日开馆前检查前一日备份状态。"},
     ],
     "tables": [
         {"id": "t1", "page": 2, "text": "性能与运维目标表\n并发用户数 | 50\n查询响应时间上限 | 1.5秒\n每日备份开始时间 | 02:00", "image_path": "assets/harbor-t1.png"},
         {"id": "t2", "page": 3, "text": "设备预算表（人民币）\n应用服务器 | 12000元\n备份存储 | 4000元\n合计 | 16000元", "image_path": "assets/harbor-t2.png"},
     ],
     "images": [{"id": "fig1", "page": 3, "path": "assets/harbor-fig1.png", "caption": "图1为虚构设计示意：检索、借阅、归还的目标响应时间依次为0.8秒、1.1秒、1.0秒。这些是方案目标值，不是实测结果。"}],
     "figure_labels": ["Search", "Borrow", "Return"], "figure_values": [0.8, 1.1, 1.0]},
    {"doc_id": "orchard", "title": "果园物资库存系统方案", "page_count": 3,
     "sections": [
         {"id": "s1", "title": "范围与对象", "page": 1, "text": "果园物资库存系统用于管理生产物资的入库、领用和库存预警。试点覆盖2个仓库和600种物资。系统不处理销售订单和财务结算。"},
         {"id": "s2", "title": "领用与预警", "page": 2, "text": "物资领用必须先提交申请，再由仓库管理员审核。单次领用数量超过100件时，还须由主管复核。可用库存低于20件时触发补货提醒，提醒每6小时汇总一次。"},
         {"id": "s3", "title": "权限与留痕", "page": 2, "text": "申请人可以查看本人申请；仓库管理员负责库存登记；主管负责大额领用复核。库存调整必须记录调整原因。操作日志保留365天。主管不得复核自己提交的申请。"},
         {"id": "s4", "title": "实施与容灾", "page": 3, "text": "项目分为需求、开发和试运行三个阶段，总周期为6周。验收要求库存账实相符率不低于98%。故障恢复时间目标为30分钟，允许的数据丢失时间窗口为1小时。"},
     ],
     "tables": [
         {"id": "t1", "page": 2, "text": "性能与备份目标表\n并发用户数 | 30\n入库保存响应时间上限 | 2秒\n完整备份频率 | 每日1次", "image_path": "assets/orchard-t1.png"},
         {"id": "t2", "page": 3, "text": "试点物资安全库存表\n包装箱 | 50件\n标签纸 | 80件\n防护手套 | 40件", "image_path": "assets/orchard-t2.png"},
     ],
     "images": [{"id": "fig1", "page": 3, "path": "assets/orchard-fig1.png", "caption": "图1为虚构设计示意：入库、领用、查询的目标响应时间依次为1.6秒、1.8秒、0.9秒。这些是方案目标值，不是实测结果。"}],
     "figure_labels": ["Receive", "Issue", "Search"], "figure_values": [1.6, 1.8, 0.9]},
    {"doc_id": "atlas", "title": "星图志愿活动排班系统方案", "page_count": 3,
     "sections": [
         {"id": "s1", "title": "目标与规模", "page": 1, "text": "星图志愿活动排班系统用于活动发布、报名和班次分配。试点服务300名志愿者，同时管理最多12场活动。系统不收取报名费，也不处理交通报销。"},
         {"id": "s2", "title": "报名与排班", "page": 2, "text": "每名志愿者每周最多参加3个班次。单个班次时长为2小时。报名在活动开始前24小时截止；退出申请在活动开始前12小时截止。同一时段不得安排两个班次。"},
         {"id": "s3", "title": "角色与隐私", "page": 2, "text": "志愿者可以维护自己的可用时段，活动组织者可以审核报名并生成排班。公开排班表仅显示志愿者编号，不显示联系电话。排班修改记录保留90天。"},
         {"id": "s4", "title": "交付与通知", "page": 3, "text": "项目建设周期为5周。排班确认后，系统在10分钟内发送站内通知。发生班次冲突时阻止发布，并要求组织者调整。验收要求全部冲突测试用例均能被识别。"},
     ],
     "tables": [
         {"id": "t1", "page": 2, "text": "性能与容量目标表\n并发用户数 | 80\n报名提交响应时间上限 | 1秒\n每场活动报名人数上限 | 60人", "image_path": "assets/atlas-t1.png"},
         {"id": "t2", "page": 3, "text": "示例活动岗位需求表\n签到引导 | 4人\n场地维护 | 6人\n物资发放 | 5人\n合计 | 15人", "image_path": "assets/atlas-t2.png"},
     ],
     "images": [{"id": "fig1", "page": 3, "path": "assets/atlas-fig1.png", "caption": "图1为虚构设计示意：报名、排班、查询的目标响应时间依次为0.8秒、1.4秒、0.6秒。这些是方案目标值，不是实测结果。"}],
     "figure_labels": ["Register", "Schedule", "Search"], "figure_values": [0.8, 1.4, 0.6]},
]


QUESTION_ROWS = {
    "harbor": [
        ("港湾系统的试点规模为多少名读者？", "2000名读者", "text", ["text:s1"]),
        ("港湾系统每日服务时间是什么？", "每日08:00至22:00", "text", ["text:s1"]),
        ("港湾系统最多允许同时借阅多少份资料？", "3份资料", "text", ["text:s2"]),
        ("港湾系统的借阅审计日志保留多久？", "180天", "text", ["text:s3"]),
        ("港湾系统的查询响应时间上限是多少？", "1.5秒", "table", ["table:t1"]),
        ("港湾系统的设备总预算是多少？", "16000元", "table", ["table:t2"]),
        ("港湾系统首次借阅期限和试点建设周期分别是多少？", "首次借阅期限14天，试点建设周期4周", "cross_section", ["text:s2", "text:s4"]),
        ("港湾系统每天何时开始备份，谁负责开馆前检查备份状态？", "每日02:00开始备份，由管理员检查", "cross_section", ["table:t1", "text:s4"]),
        ("港湾系统采用哪一家云服务商？", "文档未说明云服务商", "unanswerable", []),
        ("港湾系统项目负责人的手机号码是多少？", "文档未提供项目负责人手机号码", "unanswerable", []),
    ],
    "orchard": [
        ("果园系统试点覆盖多少个仓库？", "2个仓库", "text", ["text:s1"]),
        ("果园系统是否处理销售订单和财务结算？", "不处理销售订单和财务结算", "text", ["text:s1"]),
        ("果园系统单次领用超过多少件时需要主管复核？", "超过100件", "text", ["text:s2"]),
        ("果园系统的操作日志保留多久？", "365天", "text", ["text:s3"]),
        ("果园系统入库保存响应时间上限是多少？", "2秒", "table", ["table:t1"]),
        ("果园系统标签纸的安全库存是多少？", "80件", "table", ["table:t2"]),
        ("果园系统库存提醒多久汇总一次，故障恢复时间目标是多少？", "每6小时汇总一次，故障恢复时间目标30分钟", "cross_section", ["text:s2", "text:s4"]),
        ("果园系统需要主管复核的数量条件是什么，主管能否复核自己的申请？", "单次领用超过100件需要主管复核，主管不得复核自己的申请", "cross_section", ["text:s2", "text:s3"]),
        ("果园系统使用的数据库品牌是什么？", "文档未说明数据库品牌", "unanswerable", []),
        ("果园系统的实际上线日期是哪一天？", "文档未提供实际上线日期", "unanswerable", []),
    ],
    "atlas": [
        ("星图系统的试点服务多少名志愿者？", "300名志愿者", "text", ["text:s1"]),
        ("星图系统每名志愿者每周最多参加几个班次？", "3个班次", "text", ["text:s2"]),
        ("星图系统报名在活动开始前多久截止？", "24小时", "text", ["text:s2"]),
        ("星图系统的公开排班表显示什么，是否显示联系电话？", "仅显示志愿者编号，不显示联系电话", "text", ["text:s3"]),
        ("星图系统每场活动报名人数上限是多少？", "60人", "table", ["table:t1"]),
        ("星图系统示例活动的岗位需求合计多少人？", "15人", "table", ["table:t2"]),
        ("星图系统单个班次时长是多少，排班确认后多久发送通知？", "班次时长2小时，确认后10分钟内发送站内通知", "cross_section", ["text:s2", "text:s4"]),
        ("星图系统排班修改记录保留多久，项目建设周期为几周？", "修改记录保留90天，建设周期5周", "cross_section", ["text:s3", "text:s4"]),
        ("星图系统短信供应商叫什么？", "文档未说明短信供应商", "unanswerable", []),
        ("星图系统的年度运维费用是多少？", "文档未提供年度运维费用", "unanswerable", []),
    ],
}

REQUIRED_TERMS = {
    "harbor": [["2000"], ["08:00", "22:00"], ["3"], ["180"], ["1.5"], ["16000"], ["14", "4"], ["02:00", "管理员"], [], []],
    "orchard": [["2"], ["不", "销售", "财务"], ["100"], ["365"], ["2"], ["80"], ["6", "30"], ["100", "不得", "自己"], [], []],
    "atlas": [["300"], ["3"], ["24"], ["编号", "不", "电话"], ["60"], ["15"], ["2", "10"], ["90", "5"], [], []],
}


def page_text(page, text: str, y: float, size: int = 12) -> float:
    """Fixed character wrap fits Chinese text in a 515-point content width."""
    for paragraph in text.splitlines():
        chunks = [paragraph[index:index + 38] for index in range(0, len(paragraph), 38)] or [""]
        for line in chunks:
            page.insert_text((40, y), line, fontname="china-s", fontsize=size, color=(0.12, 0.18, 0.25))
            y += size * 1.65
    return y + 10


def table_image(text: str, target: Path) -> None:
    with fitz.open() as pdf:
        page = pdf.new_page(width=600, height=190)
        page.draw_rect(fitz.Rect(12, 12, 588, 178), color=(0.23, 0.4, 0.57), fill=(0.96, 0.98, 1))
        page_text(page, text, 40, 13)
        page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3), alpha=False).save(target)


def figure(document: dict, target: Path) -> None:
    with fitz.open() as pdf:
        page = pdf.new_page(width=600, height=280)
        page.insert_text((28, 26), "FICTIONAL DESIGN TARGETS (seconds)", fontsize=15, color=(0.12, 0.25, 0.4))
        page.draw_line((55, 215), (560, 215), color=(0.3, 0.3, 0.3))
        for index, (label, value) in enumerate(zip(document["figure_labels"], document["figure_values"])):
            x = 100 + index * 160
            page.draw_rect(fitz.Rect(x, 215 - value * 78, x + 65, 215), fill=(0.2, 0.48, 0.67), color=None)
            page.insert_text((x + 16, 203 - value * 78), str(value), fontsize=13)
            page.insert_text((x - 4, 238), label, fontsize=12)
        page.insert_text((28, 268), "Synthetic example, not measured system performance.", fontsize=10)
        page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False).save(target)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "assets").mkdir(exist_ok=True)
    questions = []
    for original in DOCUMENTS:
        document = {key: value for key, value in original.items() if not key.startswith("figure_")}
        document["source_pdf"] = f"{document['doc_id']}.pdf"
        document["fixture_notice"] = "Fictional manually structured specification; not a parser or model benchmark result."
        for table in document["tables"]:
            table_image(table["text"], DATA / table["image_path"])
        figure(original, DATA / document["images"][0]["path"])
        with fitz.open() as pdf:
            for number in range(1, 4):
                page = pdf.new_page(width=595, height=842)
                y = page_text(page, document["title"], 48, 17)
                y = page_text(page, "虚构课程示例；所有数值均为方案设定。", y, 10)
                for section in document["sections"]:
                    if section["page"] == number:
                        y = page_text(page, section["title"], y + 12, 14)
                        y = page_text(page, section["text"], y, 12)
                for table in document["tables"]:
                    if table["page"] == number:
                        y = page_text(page, table["text"], y + 14, 12)
                if number == 3:
                    page.insert_image(fitz.Rect(42, y + 12, 552, y + 250), filename=str(DATA / document["images"][0]["path"]))
                    page_text(page, document["images"][0]["caption"], y + 275, 10)
                page.insert_text((280, 816), f"{number} / 3", fontsize=10)
            pdf.save(DATA / document["source_pdf"])
        (DATA / f"{document['doc_id']}.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for index, (question, answer, category, evidence) in enumerate(QUESTION_ROWS[document["doc_id"]], 1):
            questions.append({"id": f"{document['doc_id']}-{index:02}", "doc_id": document["doc_id"],
                              "question": question, "expected_answer": answer,
                              "answerable": category != "unanswerable", "category": category,
                              "required_terms": REQUIRED_TERMS[document["doc_id"]][index - 1],
                              "expected_evidence_ids": [f"{document['doc_id']}:{item}" for item in evidence]})
    (BASE / "questions.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
