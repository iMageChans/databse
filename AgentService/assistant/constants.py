# 关系选项
RELATIONSHIP_OPTIONS = {
    'free': ['规划师', '顾问', '理财搭子'],
    'premium': ['灵魂伴侣', '心动对象', '甜蜜伴侣', '谜一样的TA', '霸道总裁', '超凡智者', '机智军师', '智慧助理', '财富守护神']
}

# 昵称选项
NICKNAME_OPTIONS = {
    'free': ['知心财友', '金钱守护者', '财富搭档'],
    'premium': ['掌心宠', '天使', '甜心', '财务智囊', '资本大佬', '掌控者', '造梦者', '探索者', '魔法师']
}

# 性格选项
PERSONALITY_OPTIONS = {
    'free': ['元气炸裂', '暖心陪伴'],
    'premium': ['温柔体贴', '戏精本精', '冷静理性',
                '诗意哲人', '毒舌段子手', '数据大神']
}

# 付费关系选项
PREMIUM_RELATIONSHIP_OPTIONS = [
    "BF", "GF", "BFF", "Muse", "Mystery", "Crush", 
    "Money Guru", "Butler", "Boss", "Customization"
]

# 付费昵称选项
PREMIUM_NICKNAME_OPTIONS = [
    "Babe", "Angel", "Champ", "Sweetie", "Stranger", 
    "Master", "Bestie", "Cutie", "Rookie", "Customization"
]

# 付费性格选项
PREMIUM_PERSONALITY_OPTIONS = [
    "Friendly & Warm", "Romantic & Flirty", "Professional & Smart", 
    "Fun & Humorous", "Calm & Caring", "Unique & Fantasy", "Customization"
]

# 免费关系选项
FREE_RELATIONSHIP_OPTIONS = ["规划师", "顾问", "理财搭子"]

# 免费昵称选项
FREE_NICKNAME_OPTIONS = ["知心财友", "金钱守护者", "财富搭档"]

# 免费性格选项
FREE_PERSONALITY_OPTIONS = ["元气炸裂", "暖心陪伴"]

# 判断是否是自定义值
def is_custom_value(field, value):
    all_options = RELATIONSHIP_OPTIONS if field == 'relationship' else \
                 NICKNAME_OPTIONS if field == 'nickname' else \
                 PERSONALITY_OPTIONS
    
    all_values = all_options['free'] + all_options['premium']
    return value not in all_values 