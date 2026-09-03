"""A1 客户画像采集 mock 数据（P5.1a）。

模拟「官网爬取 + 企查查/工商数据」两个数据源的返回，用于开发/测试阶段
（真实数据源有反爬限制，需权限；见 AI能力边界 A1 数据源约束）。

每条 mock 对应一个目标公司，给出"真值"(企业公开档案) 供准确率测量。
准确率底线：关键字段(公司名/行业/规模) 命中率 ≥ 85%。
"""
import json

# 目标公司 → 真实公开档案真值（用于准确率核对）
CUSTOMER_TRUE_PROFILES = {
    "某某科技有限公司": {
        "company": "某某科技有限公司",
        "industry": "工业软件",
        "scale": "大型",
        "main_business": "工业软件研发与销售",
        "website": "https://www.mou-mou.example.com",
        "background": "专注工业软件 20 年，服务制造业客户",
    },
    "蓝海智能装备股份": {
        "company": "蓝海智能装备股份",
        "industry": "智能制造 / 装备制造",
        "scale": "中大型",
        "main_business": "智能产线与工业机器人",
        "website": "https://www.lanhai.example.com",
        "background": "上市公司，华东制造业龙头",
    },
    "启明教育科技": {
        "company": "启明教育科技",
        "industry": "教育信息化",
        "scale": "中型",
        "main_business": "K12 智慧课堂解决方案",
        "website": "https://www.qiming.example.com",
        "background": "民办教育信息化服务商",
    },
}

# 模拟「官网 + 工商」爬取原始文本（喂给 A1 LLM 的输入，替代真实爬取）
CUSTOMER_RAW_SOURCES = {
    "某某科技有限公司": (
        "官网：某某科技有限公司，专营工业软件，自研 MES/ERP 系统，员工 800 人，"
        "注册资本 5000 万，成立 2005 年，面向大型制造企业。"
    ),
    "蓝海智能装备股份": (
        "工商：蓝海智能装备股份，股份有限公司，经营范围含智能产线、工业机器人集成，"
        "注册资本 3 亿，成立 2012 年，员工 1500 人，华东智能制造龙头。"
    ),
    "启明教育科技": (
        "官网：启明教育科技，深耕 K12 智慧课堂，提供软硬件一体化方案，"
        "员工 300 人，注册资本 1000 万，成立 2018 年，服务数百所学校。"
    ),
}


def load_true_profile(company: str) -> dict:
    """取一个公司的真值档案（准确率测量用）。"""
    return CUSTOMER_TRUE_PROFILES.get(company, {})


def load_raw_source(company: str) -> str:
    """取一个公司的原始数据源文本（喂给 A1 LLM 的输入）。"""
    return CUSTOMER_RAW_SOURCES.get(company, "")


def all_companies() -> list[str]:
    return list(CUSTOMER_TRUE_PROFILES.keys())


if __name__ == "__main__":
    print(json.dumps(CUSTOMER_TRUE_PROFILES, ensure_ascii=False, indent=2))


# ============ A3 需求提炼 mock 数据（P5.2a）============
# 示例沟通记录/转写文本 + 真值：每条沟通记录应提炼的有效需求（人工确认后保留的）
# 准确率底线：候选需求有效率 ≥70%（确认后被删/大改=低效）
NOTES_TRUE_REQUIREMENTS = {
    "客户A第一次沟通": {
        "note": (
            "客户说他们现在客服响应很慢，客户咨询要等很久，希望能做个自动回复。"
            "另外他们觉得现有系统报表太乱，想要一个直观的看板，能看每天的咨询量。"
            "还说下个月有活动，想临时加个优惠券功能。"
        ),
        # 真值：从这段沟通应提炼出的有效需求（人工确认后会保留的）
        "true_requirements": [
            "自动回复客服咨询",
            "咨询量数据看板",
            "临时优惠券功能",
        ],
    },
    "客户B方案讨论": {
        "note": (
            "讨论了上线部署方案。技术负责人说希望支持私有化部署，数据不出内网。"
            "运营想要一个用户画像功能，能按标签筛选客户。"
            "提到现有系统没有消息通知，希望有新需求时能推送到企业微信。"
        ),
        "true_requirements": [
            "私有化部署支持",
            "用户标签画像",
            "企业微信消息通知",
        ],
    },
}


def load_note_text(key: str) -> str:
    return NOTES_TRUE_REQUIREMENTS.get(key, {}).get("note", "")


def load_true_requirements(key: str) -> list[str]:
    return NOTES_TRUE_REQUIREMENTS.get(key, {}).get("true_requirements", [])


def all_notes() -> list[str]:
    return list(NOTES_TRUE_REQUIREMENTS.keys())


# ============ A4 答疑 mock 数据（P5.3a）============
# 模拟知识库条目（全平台共通，有 id 供引用溯源）+ 示例问题用例
# 准确率底线：命中回答引用有效 ≥90%（引用能追溯到知识库对应条目）
KNOWLEDGE_ITEMS = [
    {"id": 1, "title": "什么是Agent", "body": "Agent 是能自主执行任务的 AI 智能体，可调用工具、自主学习、完成目标。"},
    {"id": 2, "title": "如何部署Agent", "body": "部署 Agent 需先配置模型服务，安装依赖，设置环境变量，再启动服务并注册工具。"},
    {"id": 3, "title": "私有化部署方案", "body": "私有化部署将模型和数据部署在内网/本地，数据不出内网，保障数据安全。"},
    {"id": 4, "title": "企业微信通知接入", "body": "通过企业微信 Webhook 推送消息，配置机器人地址即可实现需求变更通知。"},
]

# 示例问题 → 应命中的知识条目 id（真值，供引用有效率测量）
QA_TRUE_HITS = {
    "什么是agent": 1,
    "agent怎么部署": 2,
    "如何私有化部署": 3,
    "企业微信怎么通知": 4,
}


def load_knowledge_items() -> list[dict]:
    return KNOWLEDGE_ITEMS


def load_qa_cases() -> dict:
    return QA_TRUE_HITS
