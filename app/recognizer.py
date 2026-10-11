# -*- coding: utf-8 -*-
"""智能识别模块：项目名、班级名、人名、性别的规范化与置信评分。

置信分：>=90 自动通过；60-89 建议核对；<60 人工审查（阈值可在界面改）。
识别开关关闭的类别：不做规范化，标红进人工审查（可在审查页批量忽略）。
"""
import re

SURNAMES = set(
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁"
    "杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍"
    "虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
    "程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓"
    "牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘詹束龙叶"
    "幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴胥能苍双闻莘"
    "党翟谭贡劳逄姬申扶堵冉宰郦雍却璩桑桂濮牛寿通边扈燕冀郏浦尚农温别"
    "庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘"
    "欧阳诸葛上官司徒司空司马端木"
)

STANDARD_EVENTS = {
    "50米":        ("径赛", ["50m", "50米", "五十米"]),
    "60米":        ("径赛", ["60m", "60米", "六十米"]),
    "100米":       ("径赛", ["100m", "100米", "一百米", "百米"]),
    "200米":       ("径赛", ["200m", "200米", "二百米"]),
    "400米":       ("径赛", ["400m", "400米", "四百米"]),
    "800米":       ("径赛", ["800m", "800米", "八百米"]),
    "1500米":      ("径赛", ["1500m", "1500米", "一千五百米"]),
    "3000米":      ("径赛", ["3000m", "3000米", "三千米"]),
    "5000米":      ("径赛", ["5000m", "5000米", "五千米"]),
    "100米栏":     ("径赛", ["100米栏", "100m栏", "百米栏"]),
    "110米栏":     ("径赛", ["110米栏", "110m栏"]),
    "4x100米接力": ("径赛", ["4x100接力", "4乘100接力", "4*100接力", "400米接力", "4x100m接力"]),
    "4x400米接力": ("径赛", ["4x400接力", "4乘400接力", "4*400接力", "1600米接力", "4x400m接力"]),
    "跳高":        ("田赛", ["跳高", "highjump"]),
    "跳远":        ("田赛", ["跳远", "longjump"]),
    "三级跳远":    ("田赛", ["三级跳", "三级跳远"]),
    "立定跳远":    ("田赛", ["立定跳远", "立定跳"]),
    "铅球":        ("田赛", ["铅球", "shotput"]),
    "实心球":      ("田赛", ["实心球"]),
    "铁饼":        ("田赛", ["铁饼"]),
    "标枪":        ("田赛", ["标枪"]),
    "垒球":        ("田赛", ["垒球", "掷垒球"]),
    "跳绳":        ("田赛", ["跳绳", "一分钟跳绳"]),
}

_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}


def _cn_to_int(s):
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        pass
    total, num = 0, 0
    for ch in s:
        if ch in _CN_DIGIT:
            num = _CN_DIGIT[ch]
        elif ch in _CN_UNIT:
            total += (num or 1) * _CN_UNIT[ch]
            num = 0
        else:
            return None
    return total + num


def _clean(s):
    return re.sub(r"\s+", "", str(s or "")).lower()


# ---------------- 各类识别（带开关） ----------------
def normalize_event(raw):
    """项目名 -> (标准名, 置信分)。"""
    s = _clean(raw)
    if not s:
        return "", 0
    core = re.sub(
        r"(男子|女子|男生|女生|男|女|混合|团体|个人|组|决赛|预赛|复赛|初中|高中|年级)",
        "", s)
    core = core.strip("*-—_·.")
    for name, (_t, aliases) in STANDARD_EVENTS.items():
        for alias in list(aliases) + [name]:
            if alias and (core == alias or s == alias):
                return name, 100
    best, best_len = None, 0
    for name, (_t, aliases) in STANDARD_EVENTS.items():
        for alias in list(aliases) + [name]:
            if alias and alias in core and len(alias) > best_len:
                best, best_len = name, len(alias)
    if best:
        return best, 85
    m = re.search(r"(\d+)\s*(米|m)", core)
    if m:
        dist = m.group(1)
        if "接力" in core and dist == "4":
            return "4x100米接力", 80
        name = f"{dist}米" + ("栏" if "栏" in core else "") \
               + ("接力" if "接力" in core else "")
        if name in STANDARD_EVENTS:
            return name, 85
        return name, 70
    m = re.search(r"([一二两三四五六七八九十百千]+)\s*(米|栏)", core)
    if m:
        num = _cn_to_int(m.group(1))
        if num:
            name = f"{num}米" + ("栏" if m.group(2) == "栏" else "") \
                   + ("接力" if "接力" in core else "")
            if name in STANDARD_EVENTS:
                return name, 85
            return name, 70
    return s, 40


_GRADE_MAP = [
    ("初一", r"(初[一1]|七年级|7年级)"),
    ("初二", r"(初[二2]|八年级|8年级)"),
    ("初三", r"(初[三3]|九年级|9年级)"),
    ("高一", r"(高[一1])"),
    ("高二", r"(高[二2])"),
    ("高三", r"(高[三3])"),
]


def normalize_class(raw):
    s = re.sub(r"\s+", "", str(raw or ""))
    if not s:
        return "", 0
    grade = None
    for std, pat in _GRADE_MAP:
        if re.search(pat, s):
            grade = std
            break
    m = re.search(r"[（(]\s*(\d{1,2})\s*[)）]", s)
    if not m:
        m = re.search(r"(\d{1,2})\s*班", s)
    num = m.group(1) if m else None
    if not num:
        nums = re.findall(r"\d{1,2}", s)
        if nums:
            num = nums[-1] if grade else nums[0]
    if num:
        if grade:
            return f"{grade}({int(num)})班", 100
        return f"{int(num)}班", 70
    return (s + "班") if not s.endswith("班") else s, 45


def validate_name(raw):
    s = str(raw or "").strip().replace(" ", "")
    if not s:
        return "", 0
    if not re.fullmatch(r"[\u4e00-\u9fa5·]{2,4}", s):
        if re.fullmatch(r"[A-Za-z]{2,20}", s):
            return s, 60
        return s, 30
    return (s, 100) if s[0] in SURNAMES else (s, 65)


def detect_gender(gender_raw, event_raw, group_raw):
    g = _clean(gender_raw)
    if g:
        if "男" in g or g in ("m", "male", "1", "man", "boy"):
            return "男", 100
        if "女" in g or g in ("f", "female", "0", "2", "woman", "girl"):
            return "女", 100
    e = _clean(event_raw)
    if "男子" in e or "男生" in e:
        return "男", 70
    if "女子" in e or "女生" in e:
        return "女", 70
    grp = _clean(group_raw)
    if grp:
        if "男" in grp:
            return "男", 70
        if "女" in grp:
            return "女", 70
    return "", 35


# ---------------- 综合分析（识别开关参与） ----------------
def analyze_row(class_raw, person_raw, gender_raw, event_raw, group_raw,
                switches=None):
    """对一行报名数据做识别。switches: {"event","class","name","gender": bool}

    开关关闭的类别：不规范化、保留原始值、置信压到 50（标红），
    问题文字带类别词（供审查页分组）。
    """
    sw = {"event": True, "class": True, "name": True, "gender": True}
    if switches:
        sw.update(switches)
    issues = []

    # 班级
    if sw["class"]:
        class_name, c_score = normalize_class(class_raw)
        if c_score < 90:
            issues.append(f"班级名无法完全识别（原始：{class_raw}）")
    else:
        class_name = str(class_raw or "").strip()
        c_score = 50
        issues.append(f"班级名识别已关闭，保留原始名称：{class_name}")

    # 姓名
    if sw["name"]:
        person, p_score = validate_name(person_raw)
        if p_score < 90:
            issues.append(f"姓名可疑（原始：{person_raw}）")
    else:
        person = str(person_raw or "").strip()
        p_score = 100   # 关闭识别不扣姓名分，交人工
        issues.append(f"姓名识别已关闭，保留原始名称：{person}")

    # 项目
    if sw["event"]:
        event, e_score = normalize_event(event_raw)
        if e_score < 90:
            issues.append(f"项目名可疑（原始：{event_raw}）")
    else:
        event = str(event_raw or "").strip()
        e_score = 50
        issues.append(f"项目名识别已关闭，保留原始名称：{event}")

    # 性别
    if sw["gender"]:
        gender, g_score = detect_gender(gender_raw, event_raw, group_raw)
        if not gender:
            issues.append("性别未知，需人工确认")
    else:
        gender = str(gender_raw or "").strip()
        if gender not in ("男", "女"):
            gender = ""
            g_score = 50
            issues.append("性别未填写（识别已关闭）")
        else:
            g_score = 100

    score = min(c_score, p_score, e_score)
    if not gender:
        score = min(score, 50)
    return {
        "class_name": class_name, "person": person, "gender": gender,
        "event": event, "score": score, "issues": issues,
        "raw_event": str(event_raw or ""), "raw_class": str(class_raw or ""),
    }
