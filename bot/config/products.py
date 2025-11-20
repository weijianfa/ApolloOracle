"""
产品配置
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Product:
    """产品数据类"""
    id: int
    name_zh: str
    name_en: str
    price_usd: float
    description_zh: str
    description_en: str
    input_fields: List[str]  # 需要的输入字段列表
    requires_bazi: bool = False  # 是否需要八字数据


# 产品列表配置
# 根据PRD文档：产品与定价表格
PRODUCTS: Dict[int, Product] = {
    1: Product(
        id=1,
        name_zh="每日塔罗",
        name_en="Daily Tarot Draw",
        price_usd=0.00,  # 免费 - 引流产品
        description_zh="✨ 免费体验，每日一牌指引方向\n\n让神秘的塔罗牌为您揭示今日的启示与指引。AI智能抽取专属塔罗牌，结合您的当下心境，为您提供积极正面的指引建议。无需任何输入，只需心中默念您的问题，即可获得专属于您的塔罗启示。\n\n💫 适合场景：\n• 需要方向指引时\n• 面临选择犹豫不决时\n• 想要了解今日运势时\n• 寻求心灵慰藉时",
        description_en="✨ Free Daily Guidance with Tarot\n\nLet the mystical tarot cards reveal today's insights and guidance for you. Our AI intelligently draws a personalized tarot card and provides positive, uplifting guidance based on your current state of mind. No input required - just think of your question, and receive your unique tarot revelation.\n\n💫 Perfect for:\n• When you need direction\n• Facing difficult decisions\n• Wanting to know today's fortune\n• Seeking spiritual comfort",
        input_fields=[],  # 无（或心中默念问题）
        requires_bazi=False
    ),
    2: Product(
        id=2,
        name_zh="星座周运",
        name_en="Weekly Horoscope",
        price_usd=4.99,
        description_zh="🌟 一周运势全解析，把握未来7天\n\n为您专属星座量身定制的一周运势报告，涵盖爱情、事业、健康三大核心领域。AI深度分析星象变化，为您揭示未来一周的机遇与挑战，助您提前规划，把握最佳时机。\n\n📊 报告包含：\n• 💕 爱情运势：感情发展、桃花运、关系建议\n• 💼 事业运势：工作机会、职场建议、合作机遇\n• 💪 健康运势：身体状况、养生建议、注意事项\n\n让星座智慧指引您的一周，做出更明智的选择！",
        description_en="🌟 Complete Weekly Forecast - Navigate Your Next 7 Days\n\nA personalized weekly horoscope report tailored specifically for your zodiac sign, covering three core areas: love, career, and health. Our AI deeply analyzes astrological changes to reveal opportunities and challenges for the coming week, helping you plan ahead and seize the best moments.\n\n📊 Report Includes:\n• 💕 Love Fortune: Relationship development, romance opportunities, relationship advice\n• 💼 Career Fortune: Work opportunities, workplace guidance, partnership chances\n• 💪 Health Fortune: Physical condition, wellness tips, important notes\n\nLet the wisdom of the stars guide your week and help you make wiser choices!",
        input_fields=["zodiac"],  # 需要星座 (e.g., "Taurus")
        requires_bazi=False
    ),
    3: Product(
        id=3,
        name_zh="姓名解析",
        name_en="Name Interpretation",
        price_usd=9.99,
        description_zh="🔮 揭秘名字背后的能量密码\n\n您的名字蕴含着独特的能量与命运密码。通过深度分析名字的寓意、五行属性、性格特质和人生轨迹，为您揭示名字背后的深层含义。了解您的名字如何影响您的性格、运势和人生选择。\n\n📖 报告内容：\n• ✨ 名字寓意：每个字的深层含义与象征\n• 🌈 性格特质：名字所体现的性格特征\n• ⚡ 能量分析：名字蕴含的五行能量\n• 🎯 人生建议：基于名字特质的人生指引\n\n适合想要深入了解自己、探索名字奥秘的朋友！",
        description_en="🔮 Unlock the Energy Code Behind Your Name\n\nYour name carries unique energy and destiny codes. Through in-depth analysis of name meaning, five-element attributes, personality traits, and life path, we reveal the deep meanings hidden behind your name. Discover how your name influences your personality, fortune, and life choices.\n\n📖 Report Contents:\n• ✨ Name Meaning: Deep meanings and symbols of each character\n• 🌈 Personality Traits: Characteristics reflected by your name\n• ⚡ Energy Analysis: Five-element energy contained in your name\n• 🎯 Life Guidance: Life advice based on name characteristics\n\nPerfect for those who want to deeply understand themselves and explore the mysteries of names!",
        input_fields=["name"],  # 姓名（中文或英文）+(可选：性别)或仅姓名
        requires_bazi=False
    ),
    4: Product(
        id=4,
        name_zh="生肖配对",
        name_en="Compatibility Test",
        price_usd=9.99,
        description_zh="💑 深度解析两人关系的能量匹配\n\n想知道你们是否天生一对？生肖配对分析为您揭示两人在爱情、友情或合作关系中的契合度。通过传统生肖智慧与现代AI分析，深度解读你们的性格互补、相处模式和发展潜力。\n\n💡 适用关系：\n• 💕 情侣关系：了解爱情契合度，找到相处之道\n• 👫 朋友关系：分析友谊深度，增进彼此理解\n• 🤝 合作关系：评估合作潜力，优化团队配合\n\n📊 报告包含：\n• 性格匹配度分析\n• 相处模式建议\n• 关系发展预测\n• 改善关系的方法\n\n让生肖智慧帮助您更好地经营每一段重要关系！",
        description_en="💑 Deep Analysis of Relationship Energy Compatibility\n\nWant to know if you're a perfect match? Our Zodiac Compatibility Test reveals the compatibility between two people in love, friendship, or partnership. Through traditional zodiac wisdom and modern AI analysis, we deeply interpret your personality complementarity, interaction patterns, and development potential.\n\n💡 Suitable For:\n• 💕 Romantic Relationships: Understand love compatibility, find ways to get along\n• 👫 Friendships: Analyze friendship depth, enhance mutual understanding\n• 🤝 Partnerships: Evaluate collaboration potential, optimize team synergy\n\n📊 Report Includes:\n• Personality compatibility analysis\n• Interaction pattern suggestions\n• Relationship development forecast\n• Methods to improve relationships\n\nLet zodiac wisdom help you better manage every important relationship!",
        input_fields=["zodiac_a", "zodiac_b"],  # 生肖A+生肖B（可选：gender_a, gender_b）
        requires_bazi=False
    ),
    5: Product(
        id=5,
        name_zh="生辰八字",
        name_en="Birth Bazi Chart",
        price_usd=29.99,
        description_zh="🎯 专业八字命盘深度解析\n\n八字命理是中华传统文化精髓，通过出生年月日时的天干地支组合，揭示您与生俱来的命运密码。本报告结合传统命理智慧与AI深度分析，为您提供专业详尽的八字命盘解读。\n\n📚 报告内容：\n• 🔮 命盘排盘：完整的八字四柱排盘\n• ⚖️ 五行分析：五行强弱、喜忌用神分析\n• 💼 事业财运：事业发展方向、财运走势\n• 💕 感情婚姻：感情运势、婚姻状况\n• 🏠 家庭健康：家庭关系、健康状况\n• 📅 大运流年：未来十年运势走向\n• 💡 人生建议：基于命理的专业建议\n\n适合想要深度了解自己命运、规划人生方向的朋友。专业、深入、全面！",
        description_en="🎯 Professional Bazi Destiny Analysis\n\nBazi (Eight Characters) is the essence of traditional Chinese culture. Through the combination of heavenly stems and earthly branches from your birth date and time, it reveals your innate destiny code. This report combines traditional fortune-telling wisdom with AI deep analysis to provide you with professional and detailed Bazi chart interpretation.\n\n📚 Report Contents:\n• 🔮 Chart Arrangement: Complete Bazi four-pillar chart\n• ⚖️ Five-Element Analysis: Element strength, favorable/unfavorable elements\n• 💼 Career & Wealth: Career direction, financial trends\n• 💕 Love & Marriage: Relationship fortune, marriage status\n• 🏠 Family & Health: Family relationships, health conditions\n• 📅 Major Cycles: Fortune trends for the next ten years\n• 💡 Life Guidance: Professional advice based on destiny analysis\n\nPerfect for those who want to deeply understand their destiny and plan their life direction. Professional, in-depth, and comprehensive!",
        input_fields=["birthday", "birth_time", "gender"],  # 出生日期和时间+性别（性别为必填项）
        requires_bazi=True
    ),
    6: Product(
        id=6,
        name_zh="流年运势",
        name_en="Annual Forecast",
        price_usd=19.99,
        description_zh="📅 未来一年运势全景预测\n\n基于您的出生信息，为您分析未来12个月的整体运势走向。这份年度运势报告将帮助您提前了解每个月的机遇与挑战，让您能够提前规划，把握最佳时机，避开潜在风险。\n\n🌟 报告亮点：\n• 📊 月度运势：逐月分析运势变化趋势\n• 💼 事业规划：事业发展机会与注意事项\n• 💰 财运分析：财运走势与投资建议\n• 💕 感情运势：感情发展的重要时间节点\n• 🏥 健康提醒：需要关注的健康时段\n• 🎯 重要节点：一年中的关键时间点\n• 💡 行动建议：每月最佳行动方向\n\n让您对未来一年心中有数，从容应对每一个重要时刻！",
        description_en="📅 Complete Annual Fortune Forecast for the Coming Year\n\nBased on your birth information, we analyze the overall fortune trends for the next 12 months. This annual fortune report will help you understand opportunities and challenges for each month in advance, allowing you to plan ahead, seize the best moments, and avoid potential risks.\n\n🌟 Report Highlights:\n• 📊 Monthly Fortune: Month-by-month analysis of fortune trends\n• 💼 Career Planning: Career opportunities and important notes\n• 💰 Wealth Analysis: Financial trends and investment advice\n• 💕 Love Fortune: Important time nodes for relationship development\n• 🏥 Health Reminders: Health periods to pay attention to\n• 🎯 Key Moments: Critical time points throughout the year\n• 💡 Action Suggestions: Best action directions for each month\n\nLet you have a clear picture of the coming year and face every important moment with confidence!",
        input_fields=["birthday", "gender"],  # 出生日期+性别（性别为必填项）
        requires_bazi=False
    ),
}


def get_product(product_id: int) -> Optional[Product]:
    """获取产品信息"""
    return PRODUCTS.get(product_id)


def get_all_products() -> List[Product]:
    """获取所有产品列表"""
    return list(PRODUCTS.values())


# 星座列表
ZODIAC_SIGNS = [
    ("Aries", "白羊座", "♈"),
    ("Taurus", "金牛座", "♉"),
    ("Gemini", "双子座", "♊"),
    ("Cancer", "巨蟹座", "♋"),
    ("Leo", "狮子座", "♌"),
    ("Virgo", "处女座", "♍"),
    ("Libra", "天秤座", "♎"),
    ("Scorpio", "天蝎座", "♏"),
    ("Sagittarius", "射手座", "♐"),
    ("Capricorn", "摩羯座", "♑"),
    ("Aquarius", "水瓶座", "♒"),
    ("Pisces", "双鱼座", "♓"),
]

# 生肖列表
CHINESE_ZODIAC = [
    ("Rat", "鼠", "🐭"),
    ("Ox", "牛", "🐂"),
    ("Tiger", "虎", "🐅"),
    ("Rabbit", "兔", "🐰"),
    ("Dragon", "龙", "🐲"),
    ("Snake", "蛇", "🐍"),
    ("Horse", "马", "🐴"),
    ("Goat", "羊", "🐑"),
    ("Monkey", "猴", "🐵"),
    ("Rooster", "鸡", "🐓"),
    ("Dog", "狗", "🐕"),
    ("Pig", "猪", "🐷"),
]

