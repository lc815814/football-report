# -*- coding: utf-8 -*-
"""
生成自包含 HTML 分析报告（双击即可在浏览器查看）
==================================================
内容：英超 2015/16 + 2023/24 两赛季分析图表 + 关键结论
      + 即时比分预测器
        - 2025/26 赛季（12 个联赛：五大联赛 + 葡超/荷甲/比甲/土超/苏超/奥甲/希超）
        - 2026/27 当前赛季（五大联赛：2025/26 全季 + 2026/27 已踢轮次 合并训练）
        - 欧冠 2025/26（36 队独立模型，189 场）
        - 2023/24 五大联赛 + 英超 2015/16
输出：football_analysis_report.html（单文件，图片内嵌，可随意移动）
"""

import os
import json
import base64
import datetime

import football_model as fm

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "football_data")
CHART = os.path.join(BASE, "charts")
OUT = os.path.join(BASE, "football_analysis_report.html")

# ---------------- 联赛定义 ----------------
# key: (中文名, 2025-26 文件名, 2026-27 文件名或 None)
LEAGUES_2526 = {
    "en_2526": ("英超 2025/26", "openfootball_2025-26_en.1.json", None),
    "es_2526": ("西甲 2025/26", "openfootball_2025-26_es.1.json", None),
    "de_2526": ("德甲 2025/26", "openfootball_2025-26_de.1.json", None),
    "it_2526": ("意甲 2025/26", "openfootball_2025-26_it.1.json", None),
    "fr_2526": ("法甲 2025/26", "openfootball_2025-26_fr.1.json", None),
    "pt_2526": ("葡超 2025/26", "openfootball_2025-26_pt.1.json", None),
    "nl_2526": ("荷甲 2025/26", "openfootball_2025-26_nl.1.json", None),
    "be_2526": ("比甲 2025/26", "openfootball_2025-26_be.1.json", None),
    "tr_2526": ("土超 2025/26", "openfootball_2025-26_tr.1.json", None),
    "sco_2526": ("苏超 2025/26", "openfootball_2025-26_sco.1.json", None),
    "at_2526": ("奥甲 2025/26", "openfootball_2025-26_at.1.json", None),
    "gr_2526": ("希超 2025/26", "openfootball_2025-26_gr.1.json", None),
}
# 2026/27 当前赛季（合并训练）
LEAGUES_2627 = {
    "en_2627": ("英超 2026/27（进行中）", "openfootball_2025-26_en.1.json", "openfootball_2026-27_en.1.json"),
    "es_2627": ("西甲 2026/27（进行中）", "openfootball_2025-26_es.1.json", "openfootball_2026-27_es.1.json"),
    "de_2627": ("德甲 2026/27（进行中）", "openfootball_2025-26_de.1.json", "openfootball_2026-27_de.1.json"),
    "it_2627": ("意甲 2026/27（进行中）", "openfootball_2025-26_it.1.json", "openfootball_2026-27_it.1.json"),
    "fr_2627": ("法甲 2026/27（进行中）", "openfootball_2025-26_fr.1.json", "openfootball_2026-27_fr.1.json"),
    "pt_2627": ("葡超 2026/27（进行中）", "openfootball_2025-26_pt.1.json", "openfootball_2026-27_pt.1.json"),
    "nl_2627": ("荷甲 2026/27（进行中）", "openfootball_2025-26_nl.1.json", "openfootball_2026-27_nl.1.json"),
    "en2_2627": ("英冠 2026/27（进行中）", "openfootball_2025-26_en.2.json", "openfootball_2026-27_en.2.json"),
}
# 2023/24 五大联赛（原有）
LEAGUES_2324 = {
    "en_2324": ("英超 2023/24", "openfootball_2023-24_en.1.json"),
    "es_2324": ("西甲 2023/24", "openfootball_2023-24_es.1.json"),
    "de_2324": ("德甲 2023/24", "openfootball_2023-24_de.1.json"),
    "it_2324": ("意甲 2023/24", "openfootball_2023-24_it.1.json"),
    "fr_2324": ("法甲 2023/24", "openfootball_2023-24_fr.1.json"),
}
# 日职 / 韩职（2026 当前赛季，跨年单赛季制）
LEAGUES_SINGLE = {
    "jp_2627": ("日职 J1 2026/27（进行中）", "openfootball_2026-27-jp.1.json"),
    "kr_2026": ("韩职 K1 2026（进行中）", "openfootball_2026-kr.1.json"),
}

# ---------------- 中文队名映射 ----------------
CN = {
    # 英超
    "Arsenal FC": "阿森纳", "Arsenal": "阿森纳", "Aston Villa FC": "阿斯顿维拉",
    "Aston Villa": "阿斯顿维拉", "AFC Bournemouth": "伯恩茅斯",
    "Brentford FC": "布伦特福德", "Brighton & Hove Albion FC": "布莱顿",
    "Burnley FC": "伯恩利", "Chelsea FC": "切尔西", "Chelsea": "切尔西",
    "Crystal Palace FC": "水晶宫", "Crystal Palace": "水晶宫",
    "Everton FC": "埃弗顿", "Everton": "埃弗顿", "Fulham FC": "富勒姆",
    "Liverpool FC": "利物浦", "Liverpool": "利物浦", "Leeds United FC": "利兹联",
    "Luton Town FC": "卢顿", "Manchester City FC": "曼城", "Manchester City": "曼城",
    "Manchester United FC": "曼联", "Manchester United": "曼联",
    "Newcastle United FC": "纽卡斯尔联", "Newcastle United": "纽卡斯尔联",
    "Nottingham Forest FC": "诺丁汉森林", "Sheffield United FC": "谢菲尔德联",
    "Sunderland AFC": "桑德兰", "Sunderland": "桑德兰",
    "Tottenham Hotspur FC": "热刺", "Tottenham Hotspur": "热刺",
    "West Ham United FC": "西汉姆联", "West Ham United": "西汉姆联",
    "Wolverhampton Wanderers FC": "狼队", "Leicester City": "莱斯特城",
    "Southampton": "南安普顿", "Stoke City": "斯托克城", "Swansea City": "斯旺西",
    "Watford": "沃特福德", "West Bromwich Albion": "西布罗姆维奇", "Norwich City": "诺维奇",
    # 西甲
    "Athletic Club": "毕尔巴鄂竞技", "CA Osasuna": "奥萨苏纳",
    "Club Atlético de Madrid": "马德里竞技", "Cádiz CF": "加的斯",
    "Deportivo Alavés": "阿拉维斯", "FC Barcelona": "巴塞罗那",
    "Getafe CF": "赫塔菲", "Girona FC": "赫罗纳", "Granada CF": "格拉纳达",
    "RC Celta de Vigo": "塞尔塔", "RCD Mallorca": "马略卡",
    "Rayo Vallecano de Madrid": "巴列卡诺", "Real Betis Balompié": "皇家贝蒂斯",
    "Real Madrid CF": "皇家马德里", "Real Sociedad de Fútbol": "皇家社会",
    "Sevilla FC": "塞维利亚", "UD Almería": "阿尔梅里亚",
    "UD Las Palmas": "拉斯帕尔马斯", "Valencia CF": "瓦伦西亚",
    "Villarreal CF": "比利亚雷亚尔", "Elche CF": "埃尔切",
    "Levante UD": "莱万特", "RCD Espanyol de Barcelona": "西班牙人",
    "Real Oviedo": "皇家奥维耶多",
    # 德甲
    "1. FC Heidenheim 1846": "海登海姆", "1. FC Köln": "科隆",
    "1. FC Union Berlin": "柏林联合", "1. FSV Mainz 05": "美因茨",
    "Bayer 04 Leverkusen": "勒沃库森", "Borussia Dortmund": "多特蒙德",
    "Borussia Mönchengladbach": "门兴格拉德巴赫", "Eintracht Frankfurt": "法兰克福",
    "FC Augsburg": "奥格斯堡", "FC Bayern München": "拜仁慕尼黑",
    "RB Leipzig": "莱比锡红牛", "SC Freiburg": "弗赖堡",
    "SV Darmstadt 98": "达姆施塔特", "SV Werder Bremen": "云达不莱梅",
    "TSG 1899 Hoffenheim": "霍芬海姆", "VfB Stuttgart": "斯图加特",
    "VfL Bochum 1848": "波鸿", "VfL Wolfsburg": "沃尔夫斯堡",
    "FC St. Pauli 1910": "圣保利", "Hamburger SV": "汉堡",
    # 意甲
    "AC Milan": "AC米兰", "AC Monza": "蒙扎", "ACF Fiorentina": "佛罗伦萨",
    "AS Roma": "罗马", "Atalanta BC": "亚特兰大", "Bologna FC 1909": "博洛尼亚",
    "Cagliari Calcio": "卡利亚里", "Empoli FC": "恩波利",
    "FC Internazionale Milano": "国际米兰", "Frosinone Calcio": "弗罗西诺内",
    "Genoa CFC": "热那亚", "Hellas Verona FC": "维罗纳", "Juventus FC": "尤文图斯",
    "SS Lazio": "拉齐奥", "SSC Napoli": "那不勒斯", "Torino FC": "都灵",
    "US Lecce": "莱切", "US Salernitana 1919": "萨勒尼塔纳",
    "US Sassuolo Calcio": "萨索洛", "Udinese Calcio": "乌迪内斯",
    "AC Pisa 1909": "比萨", "Como 1907": "科莫", "Parma Calcio 1913": "帕尔马",
    "US Cremonese": "克雷莫纳",
    # 法甲
    "AS Monaco FC": "摩纳哥", "Clermont Foot 63": "克莱蒙", "FC Lorient": "洛里昂",
    "FC Metz": "梅斯", "FC Nantes": "南特", "Le Havre AC": "勒阿弗尔",
    "Lille OSC": "里尔", "Montpellier HSC": "蒙彼利埃", "OGC Nice": "尼斯",
    "Olympique Lyonnais": "里昂", "Olympique de Marseille": "马赛",
    "Paris Saint-Germain FC": "巴黎圣日耳曼", "RC Strasbourg Alsace": "斯特拉斯堡",
    "Racing Club de Lens": "朗斯", "Stade Brestois 29": "布雷斯特",
    "Stade Rennais FC 1901": "雷恩", "Stade de Reims": "兰斯", "Toulouse FC": "图卢兹",
    "AJ Auxerre": "欧塞尔", "Angers SCO": "昂热", "Paris FC": "巴黎FC",
    # 葡超
    "AVS": "AVS", "CD Nacional": "国民队", "CD Santa Clara": "圣克拉拉",
    "CD Tondela": "通德拉", "CF Estrela da Amadora": "阿马多拉之星",
    "Casa Pia AC": "卡萨皮亚", "FC Alverca": "阿尔韦卡", "FC Arouca": "阿罗卡",
    "FC Famalicão": "法马利康", "FC Porto": "波尔图", "GD Estoril Praia": "埃斯托里尔",
    "Gil Vicente FC": "吉维森特", "Moreirense FC": "摩雷伦斯", "Rio Ave FC": "里奥阿维",
    "Sport Lisboa e Benfica": "本菲卡", "Sporting Clube de Braga": "布拉加",
    "Sporting Clube de Portugal": "葡萄牙体育", "Vitória Guimarães": "吉马良斯",
    # 荷甲
    "AFC Ajax": "阿贾克斯", "AZ": "AZ阿尔克马尔", "FC Groningen": "格罗宁根",
    "FC Twente '65": "特温特", "FC Utrecht": "乌得勒支", "FC Volendam": "福伦丹",
    "Feyenoord Rotterdam": "费耶诺德", "Fortuna Sittard": "锡塔德福图纳",
    "Go Ahead Eagles": "前进之鹰", "Heracles Almelo": "赫拉克勒斯",
    "NAC Breda": "布雷达", "NEC": "尼美根", "PEC Zwolle": "兹沃勒",
    "PSV": "埃因霍温", "SBV Excelsior": "精英队", "SC Heerenveen": "海伦芬",
    "Sparta Rotterdam": "鹿特丹斯巴达", "Telstar 1963": "特尔斯达",
    # 比甲
    "Cercle Brugge": "色格拉布鲁日", "Club Brugge KV": "布鲁日",
    "FCV Dender EH": "登德尔", "KAA Gent": "根特", "KRC Genk": "亨克",
    "KV Mechelen": "梅赫伦", "KVC Westerlo": "韦斯特洛",
    "Oud-Heverlee Leuven": "勒芬", "RAAL La Louviére": "拉卢维耶尔",
    "RSC Anderlecht": "安德莱赫特", "Royal Antwerp FC": "安特卫普",
    "SV Zulte Waregem": "祖尔特瓦雷赫姆", "Sint-Truidense VV": "圣图尔登",
    "Sporting Charleroi": "沙勒罗瓦", "Standard Liège": "标准列日",
    "Union Saint-Gilloise": "圣吉罗斯联合",
    # 土超
    "Alanyaspor": "阿拉尼亚体育", "Antalyaspor": "安塔利亚体育",
    "Beşiktaş": "贝西克塔斯", "Eyüpspor": "埃于普体育",
    "Fatih Karagümrük": "卡拉古姆鲁克", "Fenerbahçe": "费内巴切",
    "Galatasaray": "加拉塔萨雷", "Gaziantep FK": "加济安泰普",
    "Gençlerbirliği": "根克勒比利吉", "Göztepe": "戈兹特佩",
    "Kasımpaşa SK": "卡森柏沙", "Kayserispor": "开塞利体育",
    "Kocaelispor": "科贾埃利体育", "Konyaspor": "科尼亚体育",
    "Samsunspor": "萨姆松体育", "Trabzonspor": "特拉布宗体育",
    "Çaykur Rizespor": "里泽体育", "İstanbul Başakşehir": "伊斯坦布尔巴萨克赛尔",
    # 苏超
    "Aberdeen FC": "阿伯丁", "Celtic FC": "凯尔特人", "Dundee FC": "邓迪FC",
    "Dundee United": "邓迪联", "Falkirk FC": "福尔柯克",
    "Heart of Midlothian": "哈茨", "Hibernian FC": "希伯尼安",
    "Kilmarnock FC": "基尔马诺克", "Livingston FC": "利文斯顿",
    "Motherwell FC": "马瑟韦尔", "Rangers FC": "流浪者", "St. Mirren FC": "圣米伦",
    # 奥甲
    "Austria Wien": "奥地利维也纳", "FC Blau Weiß Linz": "蓝白林茨",
    "Grazer AK": "格拉茨AK", "LASK": "LASK林茨", "RB Salzburg": "萨尔茨堡红牛",
    "Rapid Wien": "维也纳快速", "SCR Altach": "阿尔塔奇", "SV Ried": "里德",
    "Sturm Graz": "格拉茨风暴", "TSV Hartberg": "哈特贝格",
    "WSG Tirol": "蒂罗尔", "Wolfsberger AC": "沃尔夫斯贝格",
    # 希超
    "AE Kifisias": "基菲夏", "AE Lárissa": "拉里萨", "AEK Athen": "雅典AEK",
    "Aris Saloniki": "阿瑞斯", "Asteras Tripolis": "特里波利斯",
    "Atromitos": "阿特罗米托斯", "Levadiakos": "莱瓦贾科斯",
    "OFI Heraklion": "OFI克里特", "Olympiakos Piraeus": "奥林匹亚科斯",
    "PAOK Saloniki": "PAOK塞萨洛尼基", "Panathinaikos": "帕纳辛奈科斯",
    "Panetolikos": "帕奈托利科斯", "Panserraikos": "潘塞拉伊科斯",
    "Volos NFC": "沃洛斯",
    # 欧冠 2025/26 补充
    "FC København": "哥本哈根", "FK Bodø/Glimt": "博德闪耀",
    "FK Kairat": "凯拉特", "PAE Olympiakos SFP": "奥林匹亚科斯",
    "Paphos FC": "帕福斯", "Qarabağ Ağdam FK": "卡拉巴赫",
    "Royale Union Saint-Gilloise": "圣吉罗斯联合", "SK Slavia Praha": "布拉格斯拉维亚",
    "Galatasaray SK": "加拉塔萨雷",
    # 欧冠 2026/27 新军
    "Shakhtar Donetsk": "顿涅茨克矿工", "Slovan Bratislava": "布拉迪斯拉发",
    "Viking FK": "维京", "Sabah FK": "沙巴巴库",
    # 日职 J1 2026/27
    "Yokohama F.M.": "横滨水手", "Kashima Antlers": "鹿岛鹿角",
    "Gamba Osaka": "大阪钢巴", "Urawa Reds": "浦和红钻",
    "Sanf. Hiroshima": "广岛三箭", "JEF United": "千叶市原",
    "FC Tokyo": "东京FC", "Machida Zelvia": "町田泽维亚",
    "Kashiwa Reysol": "柏太阳神", "Mito HollyHock": "水户蜀葵",
    "Grampus": "名古屋鲸八", "Shimizu S-Pulse": "清水心跳",
    "Cerezo Osaka": "大阪樱花", "F. Okayama": "冈山绿雉",
    "Avispa Fukuoka": "福冈黄蜂", "Vissel Kobe": "神户胜利船",
    "Tokyo Verdy": "东京绿茵", "Kawasaki F.": "川崎前锋",
    "Nagasaki": "长崎航海", "Kyoto Sanga": "京都不死鸟",
    # 韩职 K1 2026
    "Incheon United": "仁川联", "FC Seoul": "首尔FC",
    "Ulsan HD": "蔚山HD", "Gangwon FC": "江原FC",
    "Sangmu": "金泉尚武", "Pohang Steelers": "浦项制铁",
    "Jeonbuk": "全北现代", "Bucheon FC": "富川FC",
    "Jeju United": "济州联", "Gwangju FC": "光州FC",
    "Daejeon Hana": "大田韩亚", "FC Anyang": "安养FC",
    # 英冠 2026/27
    "Birmingham City FC": "伯明翰", "Blackburn Rovers FC": "布莱克本",
    "Bolton Wanderers FC": "博尔顿", "Bristol City FC": "布里斯托尔城",
    "Cardiff City FC": "加的夫城", "Charlton Athletic FC": "查尔顿",
    "Derby County FC": "德比郡", "Lincoln City FC": "林肯城",
    "Middlesbrough FC": "米德尔斯堡", "Millwall FC": "米尔沃尔",
    "Portsmouth FC": "朴茨茅斯", "Preston North End FC": "普雷斯顿",
    "Queens Park Rangers FC": "女王公园巡游者", "Wrexham AFC": "雷克瑟姆",
    # 2026/27 新晋球队（竞彩在售可匹配）
    "Willem II Tilburg": "威廉二世", "Ipswich Town FC": "伊普斯维奇",
    "RC Deportivo La Coruña": "拉科鲁尼亚", "Real Racing Club de Santander": "桑坦德竞技",
}


def img_b64(rel):
    fp = os.path.join(CHART, rel)
    if not os.path.exists(fp):
        return None
    with open(fp, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def load_open(code, fname, season_name, skip_unplayed=True):
    return fm.load_matches_openfootball(os.path.join(DATA, fname), season_name, skip_unplayed=skip_unplayed)


def league_note(fname):
    """返回 (总场次, 已录入比分场次)"""
    fp = os.path.join(DATA, fname)
    j = json.load(open(fp, encoding="utf-8"))
    total = len(j.get("matches", []))

    def _ft(m):
        s = m.get("score")
        if isinstance(s, dict):
            return s.get("ft")
        if isinstance(s, (list, tuple)) and len(s) == 2:
            return s
        return None

    played = sum(1 for m in j.get("matches", []) if _ft(m))
    return total, played

def halftime_ratio():
    """统计全部数据中有半场比分的比赛，返回上半场进球占全场进球的真实比例。
    用于半全场预测时把泊松期望拆分为上下半场。无数据时回退经验值 0.45。"""
    ht_g, ft_g = 0, 0
    for fn in os.listdir(DATA):
        if not (fn.endswith(".json") and (fn.startswith("openfootball") or fn.startswith("cl_"))):
            continue
        try:
            j = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
        except Exception:
            continue
        for m in j.get("matches", []):
            s = m.get("score")
            if not isinstance(s, dict):
                continue
            ht, ft = s.get("ht"), s.get("ft")
            if not (isinstance(ht, (list, tuple)) and len(ht) == 2 and
                    isinstance(ft, (list, tuple)) and len(ft) == 2):
                continue
            if ht[0] is None or ft[0] is None:
                continue
            ht_g += ht[0] + ht[1]
            ft_g += ft[0] + ft[1]
    if ft_g <= 0:
        return 0.45
    return ht_g / ft_g


def model_params(matches):
    poisson = fm.PoissonModel().fit(matches)
    elo_df, _, _ = fm.compute_elo(matches)
    return {
        "season": matches.attrs.get("season_name", ""),
        "mu": poisson.mu_,
        "home_adv": poisson.home_adv_,
        "att": poisson.att_,
        "deff": poisson.def_,
        "elo": dict(zip(elo_df.team, elo_df.elo)),
        "form": recent_form(matches),
    }


def recent_form(matches, n=5):
    """每队最近 n 场比赛结果（该队视角 W/D/L），按日期排序取最后 n 场。"""
    d = matches.sort_values("date")
    form = {}
    for _, r in d.iterrows():
        hf, af = "W", "L"
        if r.home_goals == r.away_goals:
            hf = af = "D"
        elif r.home_goals < r.away_goals:
            hf, af = "L", "W"
        form.setdefault(r.home, []).append(hf)
        form.setdefault(r.away, []).append(af)
    return {t: "".join(v[-n:]) for t, v in form.items()}


def load_merged(name, f2526, f2627):
    """2025/26 全季 + 2026/27 已踢轮次合并训练（当前赛季最新状态）"""
    m1 = load_open(name, f2526, name)
    parts = [m1]
    if f2627:
        fp = os.path.join(DATA, f2627)
        if os.path.exists(fp):
            m2 = load_open(name + "·已踢", f2627, name, skip_unplayed=True)
            if len(m2) > 0:
                parts.append(m2)
    import pandas as pd
    m = pd.concat(parts, ignore_index=True)
    m.attrs["season_name"] = name
    return m


def standings_rows(matches, poisson):
    st = fm.build_standings(matches, poisson=poisson)
    rows = []
    for _, r in st.head(8).iterrows():
        rows.append((int(r["rank"]), r["team"], int(r.points),
                     f"{r.win}胜{r.draw}平{r.loss}负", f"{int(r.gf)}/{int(r.ga)}",
                     f"{r.xpts:.0f}", f"{r.xgd:+.0f}"))
    return rows


def build():
    js_params = {}
    m_holders = {}

    # 2025/26 十二联赛 + 2026/27 合并 + 2023/24 + 2015/16
    for key, (name, f2526, f2627) in LEAGUES_2526.items():
        m = load_merged(name, f2526, f2627)
        js_params[key] = model_params(m)
        js_params[key]["league"] = name
        js_params[key]["form_src"] = "2025/26 赛季末"
        t, p = league_note(f2526)
        js_params[key]["data_note"] = f"{p}/{t} 场"
        m_holders[key] = m
    for key, (name, f2526, f2627) in LEAGUES_2627.items():
        m = load_merged(name, f2526, f2627)
        js_params[key] = model_params(m)
        js_params[key]["league"] = name
        js_params[key]["form_src"] = "2026/27 已踢"
        t, p = league_note(f2526)
        js_params[key]["data_note"] = f"{p}/{t} 场（2025/26）+ 2026/27 已踢"
        m_holders[key] = m
    for key, (name, fname) in LEAGUES_2324.items():
        m = load_open(key, fname, name)
        js_params[key] = model_params(m)
        js_params[key]["league"] = name
        js_params[key]["form_src"] = "2023/24 赛季末"
        m_holders[key] = m
    # 日职 / 韩职（2026 当前赛季已踢比分）
    for key, (name, fname) in LEAGUES_SINGLE.items():
        m = load_open(key, fname, name, skip_unplayed=True)
        js_params[key] = model_params(m)
        js_params[key]["league"] = name
        js_params[key]["form_src"] = "2026 当前赛季"
        m_holders[key] = m
    # 数据完整度按赛程总场次标注：J1 2026/27 为 20 队×38 轮=380 场；K1 2026 为 12 队×33 轮=198 场
    total_map = {"jp_2627": 380, "kr_2026": 198}
    for key, (name, fname) in LEAGUES_SINGLE.items():
        p = league_note(fname)[1]
        js_params[key]["data_note"] = f"{p}/{total_map[key]} 场"

    m1516 = fm.load_matches(os.path.join(DATA, "m_2_27.json"))
    m1516.attrs["season_name"] = fm.SEASON_NAME
    js_params["s1516"] = model_params(m1516)
    js_params["s1516"]["league"] = "英超 2015/16"
    js_params["s1516"]["form_src"] = "2015/16 赛季末"
    m_holders["s1516"] = m1516

    # 欧冠 2025/26 独立模型
    cl = fm.load_matches_cl(os.path.join(DATA, "cl_2025-26.json"))
    js_params["cl2526"] = model_params(cl)
    js_params["cl2526"]["league"] = "欧冠 2025/26"
    js_params["cl2526"]["form_src"] = "欧冠 2025/26"
    m_holders["cl2526"] = cl
    print("CL 2025/26: %d matches, %d teams" % (len(cl), cl.home.nunique()))
    print("2026/27 已踢: 英超%d 场" % len(load_open("x", "openfootball_2026-27_en.1.json", "x", skip_unplayed=True)))

    # ---- 2026/27 已踢数据（当前状态，用于近5场）----
    # 欧冠 2026/27 首轮已踢（真实比分）+ 2026/27 联赛已踢 → 当前赛季状态
    cl27_r1 = None
    fp_r1 = os.path.join(DATA, "cl_2026-27_r1.json")
    if os.path.exists(fp_r1):
        cl27_r1 = fm.load_matches_cl(fp_r1, "欧冠 2026/27")
    cl27_parts = []
    if cl27_r1 is not None and len(cl27_r1):
        cl27_parts.append(cl27_r1)
    for code in ["en.1", "es.1", "de.1", "it.1", "fr.1", "pt.1", "nl.1"]:
        fp27 = os.path.join(DATA, f"openfootball_2026-27_{code}.json")
        if os.path.exists(fp27):
            m27 = fm.load_matches_openfootball(fp27, "x", skip_unplayed=True)
            if len(m27):
                cl27_parts.append(m27)
    cl27_form_all = {}
    if cl27_parts:
        import pandas as _pd
        cl27_all = _pd.concat(cl27_parts, ignore_index=True)
        cl27_form_all = recent_form(cl27_all, n=5)
    print("2026/27 已有状态数据球队(欧冠+联赛合并):", len(cl27_form_all))

    # 联赛标签页 form = 欧冠+联赛合并（用户要求"最近5场含欧冠"）
    for key in LEAGUES_2627:
        js_params[key]["form"] = {
            t: cl27_form_all[t] for t in js_params[key]["att"] if t in cl27_form_all
        }
        js_params[key]["form_src"] = "2026/27 欧冠+联赛已踢"

    # ---- 欧冠 2026/27（进行中）----
    # 36 队实力 = 2025/26 欧冠模型（跨联赛可比）优先，其余用 2025/26 联赛模型；
    # 无结构化联赛数据的 4 支小国球队给中性值并标注。
    cl27_src = {
        "Arsenal FC": ("cl2526", "Arsenal FC"),
        "Aston Villa FC": ("en_2526", "Aston Villa FC"),
        "Liverpool FC": ("cl2526", "Liverpool FC"),
        "Manchester City FC": ("cl2526", "Manchester City FC"),
        "Manchester United FC": ("en_2526", "Manchester United FC"),
        "FC Barcelona": ("cl2526", "FC Barcelona"),
        "Real Madrid CF": ("cl2526", "Real Madrid CF"),
        "Club Atlético de Madrid": ("cl2526", "Club Atlético de Madrid"),
        "Real Betis Balompié": ("es_2526", "Real Betis Balompié"),
        "Villarreal CF": ("cl2526", "Villarreal CF"),
        "FC Bayern München": ("cl2526", "FC Bayern München"),
        "Borussia Dortmund": ("cl2526", "Borussia Dortmund"),
        "RB Leipzig": ("de_2526", "RB Leipzig"),
        "VfB Stuttgart": ("de_2526", "VfB Stuttgart"),
        "Paris Saint-Germain FC": ("cl2526", "Paris Saint-Germain FC"),
        "Lille OSC": ("fr_2526", "Lille OSC"),
        "Racing Club de Lens": ("fr_2526", "Racing Club de Lens"),
        "FC Internazionale Milano": ("cl2526", "FC Internazionale Milano"),
        "SSC Napoli": ("cl2526", "SSC Napoli"),
        "AS Roma": ("it_2526", "AS Roma"),
        "Como 1907": ("it_2526", "Como 1907"),
        "PSV": ("cl2526", "PSV"),
        "Feyenoord Rotterdam": ("nl_2526", "Feyenoord Rotterdam"),
        "FC Porto": ("pt_2526", "FC Porto"),
        "Sporting Clube de Portugal": ("cl2526", "Sporting Clube de Portugal"),
        "Club Brugge KV": ("cl2526", "Club Brugge KV"),
        "Galatasaray SK": ("cl2526", "Galatasaray SK"),
        "Fenerbahçe": ("tr_2526", "Fenerbahçe"),
        "SK Slavia Praha": ("cl2526", "SK Slavia Praha"),
        "FK Bodø/Glimt": ("cl2526", "FK Bodø/Glimt"),
        "LASK": ("at_2526", "LASK"),
        "AEK Athen": ("gr_2526", "AEK Athen"),
        "Shakhtar Donetsk": None,
        "Slovan Bratislava": None,
        "Viking FK": None,
        "Sabah FK": None,
    }
    # 欧冠 2026/27 首轮已踢（真实比分）+ 2026/27 联赛已踢 → 当前赛季状态
    cl27_r1 = None
    fp_r1 = os.path.join(DATA, "cl_2026-27_r1.json")
    if os.path.exists(fp_r1):
        cl27_r1 = fm.load_matches_cl(fp_r1, "欧冠 2026/27")
    cl27_parts = []
    if cl27_r1 is not None and len(cl27_r1):
        cl27_parts.append(cl27_r1)
    for code in ["en.1", "es.1", "de.1", "it.1", "fr.1", "pt.1", "nl.1"]:
        fp27 = os.path.join(DATA, f"openfootball_2026-27_{code}.json")
        if os.path.exists(fp27):
            m27 = fm.load_matches_openfootball(fp27, "x", skip_unplayed=True)
            if len(m27):
                cl27_parts.append(m27)
    cl27_form_all = {}
    if cl27_parts:
        import pandas as _pd
        cl27_all = _pd.concat(cl27_parts, ignore_index=True)
        cl27_form_all = recent_form(cl27_all, n=5)
    cl27 = {
        "season": "欧冠 2026/27（进行中）· 实力基于 2025/26 表现",
        "league": "欧冠 2026/27（进行中）",
        "mu": js_params["cl2526"]["mu"],
        "home_adv": js_params["cl2526"]["home_adv"],
        "att": {}, "deff": {}, "elo": {}, "form": {}, "form_src": {},
    }
    # ---- 跨联赛校准：以欧冠 2025/26 模型为锚，把各联赛参数平移到欧冠尺度 ----
    cl_a, cl_d, cl_e = (js_params["cl2526"]["att"], js_params["cl2526"]["deff"], js_params["cl2526"]["elo"])
    offsets = {}
    global_off = [0.0, 0.0, 0.0]
    n_off = 0
    for lk in [k for k in js_params if k.endswith("_2526")]:
        ov = [t for t in js_params[lk]["att"] if t in cl_a]
        if ov:
            o = (sum(cl_a[t] - js_params[lk]["att"][t] for t in ov) / len(ov),
                 sum(cl_d[t] - js_params[lk]["deff"][t] for t in ov) / len(ov),
                 sum(cl_e[t] - js_params[lk]["elo"][t] for t in ov) / len(ov))
            offsets[lk] = o
            for i in range(3):
                global_off[i] += o[i] * len(ov)
            n_off += len(ov)
    if n_off:
        global_off = [x / n_off for x in global_off]
    print("校准偏移(联赛→欧冠):", {k: tuple(round(x, 2) for x in v) for k, v in offsets.items()})

    for team, src in cl27_src.items():
        if src is None:
            cl27["att"][team] = 0.0
            cl27["deff"][team] = 0.0
            cl27["elo"][team] = 1500.0
            fcur = cl27_form_all.get(team) or ""
            if fcur:
                cl27["form"][team] = fcur
                cl27["form_src"][team] = f"2026/27 欧冠+联赛（{len(fcur)}场）"
            else:
                cl27["form"][team] = ""
                cl27["form_src"][team] = "暂无 2026/27 数据"
            # 2026/27 已踢不足 5 场时，用 2025/26 赛季末段补足（有该队 2025/26 联赛数据的）
            if len(cl27["form"].get(team, "")) < 5:
                for lk26 in ["tr_2526", "be_2526", "at_2526", "gr_2526", "sco_2526"]:
                    tm26 = None
                    if lk26 in js_params:
                        if team in js_params[lk26]["att"]:
                            tm26 = team
                        else:
                            _w = team.split()
                            if len(_w) > 1 and " ".join(_w[:-1]) in js_params[lk26]["att"]:
                                tm26 = " ".join(_w[:-1])
                    if tm26:
                        f26 = recent_form(m_holders[lk26], n=5).get(tm26) or ""
                        if f26:
                            cur = cl27["form"].get(team, "")
                            need = min(len(f26), 5 - len(cur))
                            cl27["form"][team] = f26[-need:] + cur
                            cl27["form_src"][team] = "2025/26末+" + cl27["form_src"][team]
                        break
        else:
            p = js_params[src[0]]
            if src[0] == "cl2526":
                cl27["att"][team] = p["att"][src[1]]
                cl27["deff"][team] = p["deff"][src[1]]
                cl27["elo"][team] = p["elo"].get(src[1], 1500.0)
            else:
                off = offsets.get(src[0], global_off)
                cl27["att"][team] = p["att"][src[1]] + off[0]
                cl27["deff"][team] = p["deff"][src[1]] + off[1]
                cl27["elo"][team] = p["elo"].get(src[1], 1500.0) + off[2]
            fcur = cl27_form_all.get(team) or cl27_form_all.get(src[1]) or ""
            if fcur:
                cl27["form"][team] = fcur
                cl27["form_src"][team] = f"2026/27 欧冠+联赛（{len(fcur)}场）"
            else:
                cl27["form"][team] = ""
                cl27["form_src"][team] = "暂无 2026/27 数据"
            # 2026/27 已踢不足 5 场时，用 2025/26 赛季末段补足（有该队 2025/26 联赛数据的）
            if len(cl27["form"].get(team, "")) < 5:
                for lk26 in ["tr_2526", "be_2526", "at_2526", "gr_2526", "sco_2526"]:
                    tm26 = None
                    if lk26 in js_params:
                        if team in js_params[lk26]["att"]:
                            tm26 = team
                        elif src[1] in js_params[lk26]["att"]:
                            tm26 = src[1]
                        else:
                            _w = team.split()
                            if len(_w) > 1 and " ".join(_w[:-1]) in js_params[lk26]["att"]:
                                tm26 = " ".join(_w[:-1])
                    if tm26:
                        f26 = recent_form(m_holders[lk26], n=5).get(tm26) or ""
                        if f26:
                            cur = cl27["form"].get(team, "")
                            need = min(len(f26), 5 - len(cur))
                            cl27["form"][team] = f26[-need:] + cur
                            cl27["form_src"][team] = "2025/26末+" + cl27["form_src"][team]
                        break
    js_params["cl2627"] = cl27
    print("CL 2026/27: %d teams（32 队有 2025/26 数据并校准，4 队中性）" % len(cl27_src))

    # ---- 图表（两个英超赛季主体） ----
    charts = {}
    for key, sub in (("s1516", "2015-16"), ("s2324", "2023-24")):
        charts[key] = {}
        d = os.path.join(CHART, sub)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".png"):
                    n = int(f.split("_")[1])
                    charts[key][n] = img_b64(os.path.join(sub, f))
        print(key, "charts:", sorted(charts[key].keys()))

    # ---- 积分榜与回测（两个英超赛季） ----
    p1516 = fm.PoissonModel().fit(m1516)
    m2324 = load_open("en_2324", LEAGUES_2324["en_2324"][1], "英超 2023/24")
    p2324 = fm.PoissonModel().fit(m2324)

    tbl = {"s1516": standings_rows(m1516, p1516),
           "s2324": standings_rows(m2324, p2324)}

    bt1516p = fm.backtest_poisson(m1516, train_weeks=28)
    bt1516m = fm.backtest_ml(m1516, train_weeks=28)
    bt2324p = fm.backtest_poisson(m2324, train_weeks=int(m2324.week.max() * 0.75))
    bt2324m = fm.backtest_ml(m2324, train_weeks=int(m2324.week.max() * 0.75))
    bt = {"s1516": (bt1516p["acc"], bt1516m["acc"], bt1516p["n"]),
          "s2324": (bt2324p["acc"], bt2324m["acc"], bt2324p["n"])}

    # 球员 Top10（2015/16）
    players = []
    try:
        pt, _ = fm.build_player_stats(m1516[m1516.week <= 7])
        if pt is not None:
            for _, r in pt.head(10).iterrows():
                players.append((_short(r.player), r.team, round(r.score, 1),
                                int(r.goals), int(r.assists)))
    except Exception:
        pass

    ht_ratio = halftime_ratio()
    print("半场进球占比(全数据统计): %.3f" % ht_ratio)

    # ---- 竞彩真实盘口（生成时抓取，嵌入报告；无需本地服务，线上同样可用）----
    odds_map = {}
    odds_list = []
    try:
        import odds_server as _os
        _ms = _os.fetch_matches()
        cn2en = {}
        for _en, _cn in CN.items():
            if _cn not in cn2en:
                cn2en[_cn] = _en
        def _pick_cn(jc_name):
            # 1) 精确（含归一化）：帕尔马 -> Parma Calcio 1913，不误配拉斯帕尔马斯
            for _cn, _en in cn2en.items():
                if _cn == jc_name or _os.norm(_cn) == _os.norm(jc_name):
                    return _en
            # 2) 竞彩别名精确（如 莱红牛 -> 莱比锡）
            _al = _os.ALIAS.get(jc_name, "")
            if _al:
                for _cn, _en in cn2en.items():
                    if _cn == _al:
                        return _en
            # 3) 宽松包含（最后兜底，如 博德闪耀 -> FK Bodø/Glimt）
            for _cn, _en in cn2en.items():
                if _os.name_match(jc_name, _cn):
                    return _en
            return None

        for _m in _ms:
            _he = _pick_cn(_m["home"])
            _ae = _pick_cn(_m["away"])
            if _he and _ae:
                _had = _m["had"] or {}
                odds_map[f"{_he}|{_ae}"] = {
                    "h": _had.get("h"), "d": _had.get("d"), "a": _had.get("a"),
                    "league": _m["league"], "date": _m["matchDate"], "time": _m["matchTime"],
                    "src": f"竞彩官方 {_m['updateDate']} {_m['updateTime']}",
                }
            _h2 = _m["had"] or {}
            _hh = _m["hhad"] or {}
            odds_list.append({
                "hn": _m["home"], "an": _m["away"], "lg": _m["league"],
                "h": _h2.get("h"), "d": _h2.get("d"), "a": _h2.get("a"),
                "hh": _hh.get("h"), "hd": _hh.get("d"), "ha": _hh.get("a"),
                "num": _m.get("matchNum", ""), "st": _m.get("status", ""),
                "gl": (_hh.get("goalLine") or ""),
            })
        print("竞彩盘口: 在售 %d 场，匹配报告 %d 场" % (len(_ms), len(odds_map)))
    except Exception as _e:
        print("竞彩盘口抓取失败（不影响报告）:", type(_e).__name__)

    html = render(js_params, charts, tbl, bt, players, ht_ratio, odds_map, odds_list)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("report saved:", OUT, f"{os.path.getsize(OUT)/1024:.0f} KB")


def _short(name, n=18):
    parts = (name or "").split()
    s = " ".join(parts[:2]) if len(parts) > 2 else (name or "")
    return s if len(s) <= n else s[:n - 1] + "…"


def render(js_params, charts, tbl, bt, players, ht_ratio, odds_map=None, odds_list=None):
    def season_card(key, title, sub):
        rows = "".join(
            f"<tr><td>{r[0]}</td><td class='tl'>{r[1]}</td><td><b>{r[2]}</b></td>"
            f"<td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td>{r[6]}</td></tr>"
            for r in tbl[key])
        img = lambda n: (f"<img src='{charts[key].get(n)}' />"
                         if charts[key].get(n) else "")
        imgs = ""
        captions = {
            1: "积分榜 TOP10", 2: "强队 Elo 走势", 3: "攻防能力矩阵",
            4: "比分分布热力图", 5: "预测概率校准", 6: "模型回测对比",
            7: "球员综合表现 TOP15", 8: "球队 xG 排名",
        }
        for n in sorted(charts[key].keys()):
            imgs += (f"<div class='card'><h3>{captions.get(n, '')}</h3>"
                     f"{img(n)}</div>")
        return f"""
        <div class="season" id="{key}">
          <h2>{title}</h2>
          <div class="meta">{sub}</div>
          <div class="grid2">
            <div class="card">
              <h3>积分榜 TOP8</h3>
              <table><thead><tr><th>#</th><th>球队</th><th>积分</th>
                <th>战绩</th><th>进/失</th><th>预期积分</th><th>预期净胜</th></tr></thead>
              <tbody>{rows}</tbody></table>
            </div>
            <div class="card">
              <h3>回测表现（胜平负准确率）</h3>
              <p>泊松模型：<b>{bt[key][0]:.1%}</b>　机器学习：<b>{bt[key][1]:.1%}</b>
                 <span class="dim">（测试 {bt[key][2]} 场，随机基线约 33%）</span></p>
              <p class="dim">泊松模型：经典统计方法，可解释强<br/>
              机器学习：GradientBoosting，特征含滚动攻防与 Elo</p>
            </div>
          </div>
          <div class="grid2">{imgs}</div>
        </div>"""

    player_html = ""
    if players:
        rows = "".join(
            f"<tr><td>{p[0]}</td><td>{p[1]}</td><td><b>{p[2]}</b></td>"
            f"<td>{p[3]}</td><td>{p[4]}</td></tr>" for p in players)
        player_html = f"""
        <div class="card">
          <h3>球员综合表现 TOP10（2015/16 前 7 轮）</h3>
          <table><thead><tr><th>球员</th><th>球队</th><th>评分</th>
            <th>进球</th><th>助攻</th></tr></thead><tbody>{rows}</tbody></table>
        </div>"""

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 联赛选择器选项（欧冠 26/27 + 欧冠 25/26 + 2026/27 + 2025/26 + 2023/24 + 2015/16）
    league_opts = [("cl2627", "欧冠 2026/27（进行中）"),
                   ("cl2526", "欧冠 2025/26"),
                   ("en_2627", "英超 2026/27（进行中）"),
                   ("es_2627", "西甲 2026/27（进行中）"),
                   ("de_2627", "德甲 2026/27（进行中）"),
                   ("it_2627", "意甲 2026/27（进行中）"),
                   ("fr_2627", "法甲 2026/27（进行中）"),
                   ("pt_2627", "葡超 2026/27（进行中）"),
                   ("nl_2627", "荷甲 2026/27（进行中）"),
                   ("en2_2627", "英冠 2026/27（进行中）"),
                   ("jp_2627", "日职 J1 2026/27（进行中）"),
                   ("kr_2026", "韩职 K1 2026（进行中）"),
                   ("en_2526", "英超 2025/26"), ("es_2526", "西甲 2025/26"),
                   ("de_2526", "德甲 2025/26"), ("it_2526", "意甲 2025/26"),
                   ("fr_2526", "法甲 2025/26"), ("pt_2526", "葡超 2025/26"),
                   ("nl_2526", "荷甲 2025/26"), ("be_2526", "比甲 2025/26"),
                   ("tr_2526", "土超 2025/26"), ("sco_2526", "苏超 2025/26"),
                   ("at_2526", "奥甲 2025/26"), ("gr_2526", "希超 2025/26"),
                   ("en_2324", "英超 2023/24"), ("es_2324", "西甲 2023/24"),
                   ("de_2324", "德甲 2023/24"), ("it_2324", "意甲 2023/24"),
                   ("fr_2324", "法甲 2023/24"), ("s1516", "英超 2015/16")]
    # 数据完整度标注（不足 95% 显示）
    import re as _re
    opt_final = []
    for k, n in league_opts:
        note = js_params.get(k, {}).get("data_note")
        if note:
            nums = _re.findall(r"\d+", note)
            try:
                if len(nums) >= 2 and int(nums[0]) < int(nums[1]) * 0.95:
                    n += "（数据不全 " + note + "）"
            except Exception:
                pass
        opt_final.append((k, n))
    league_html = "".join(
        f'<option value="{k}">{n}</option>' for k, n in opt_final)
    league_order = [k for k, _ in league_opts]

    cn_json = json.dumps(CN, ensure_ascii=False)
    league_order_json = json.dumps(league_order)
    odds_map_json = json.dumps(odds_map or {}, ensure_ascii=False)
    odds_list_json = json.dumps(odds_list or [], ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>足球分析模型 · 分析报告</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: "Microsoft YaHei", system-ui, sans-serif; background: #0f172a;
         color: #e2e8f0; line-height: 1.6; padding: 20px; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; }}
  header {{ text-align: center; padding: 28px 0 10px; }}
  header h1 {{ font-size: 30px; color: #fff; }}
  header p {{ color: #94a3b8; margin-top: 6px; }}
  #oddsStatus {{ display: inline-block; margin-top: 10px; padding: 5px 14px; border-radius: 999px;
             font-size: 13px; border: 1px solid #334155; background: #1e293b; color: #94a3b8; }}
  #oddsStatus.ok {{ border-color: #22c55e; color: #86efac; background: rgba(34,197,94,.12); }}
  #oddsStatus.bad {{ border-color: #f59e0b; color: #fcd34d; background: rgba(245,158,11,.12); }}
  .tabs {{ display: flex; gap: 10px; justify-content: center; margin: 22px 0; flex-wrap: wrap; }}
  .tab {{ padding: 10px 22px; border-radius: 999px; cursor: pointer;
          background: #1e293b; border: 1px solid #334155; color: #cbd5e1; }}
  .tab.active {{ background: #2e86ab; color: #fff; border-color: #2e86ab; }}
  .season {{ display: none; }}
  .season.show {{ display: block; }}
  h2 {{ color: #fff; margin: 10px 0 4px; }}
  .meta {{ color: #94a3b8; font-size: 13px; margin-bottom: 14px; }}
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 900px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px;
          padding: 16px; margin-bottom: 16px; }}
  .card h3 {{ color: #7dd3fc; font-size: 15px; margin-bottom: 10px; }}
  .card img {{ width: 100%; border-radius: 8px; background: #fff; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 7px 8px; text-align: center; border-bottom: 1px solid #334155; }}
  th {{ color: #94a3b8; font-weight: 600; }}
  td.tl {{ text-align: left; }}
  .dim {{ color: #64748b; font-size: 12px; }}
  .predictor {{ position: sticky; bottom: 12px; background: #1e293b;
    border: 1px solid #2e86ab; border-radius: 14px; padding: 14px 18px;
    box-shadow: 0 8px 30px rgba(0,0,0,.5); margin-top: 20px; }}
  .predictor h3 {{ color: #7dd3fc; margin-bottom: 8px; font-size: 15px; }}
  .prow {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
  select, button {{ padding: 8px 12px; border-radius: 8px; border: 1px solid #334155;
    background: #0f172a; color: #e2e8f0; font-size: 13px; }}
  select {{ max-width: 260px; }}
  button {{ background: #2e86ab; color: #fff; cursor: pointer; border: none; }}
  button:hover {{ background: #256f8f; }}
  .pout {{ margin-top: 10px; font-size: 13px; }}
  .pout b {{ color: #7dd3fc; }}
  .bar {{ height: 8px; border-radius: 4px; background: #334155; overflow: hidden; display: inline-block; vertical-align: middle; width: 90px; }}
  .bar i {{ display: block; height: 100%; background: #2e86ab; }}
  .tag {{ display: inline-block; padding: 2px 10px; border-radius: 999px;
         font-size: 12px; margin-bottom: 6px; }}
  .tag.same {{ background: #14532d; color: #4ade80; }}
  .tag.cross {{ background: #7c2d12; color: #fb923c; }}
  footer {{ text-align: center; color: #475569; font-size: 12px; padding: 24px 0 10px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>⚽ 足球分析模型 · 分析报告</h1>
    <p>欧冠 2026/27（进行中）+ 2025/26 完整 12 联赛 + 欧冠 2025/26 · 泊松回归 + Elo + 机器学习 · 生成于 {now}</p>
    <div id="oddsStatus">盘口服务检测中…</div>
  </header>

  <div class="tabs">
    <div class="tab active" onclick="show('s1516')">英超 2015/16（莱斯特城奇迹）</div>
    <div class="tab" onclick="show('s2324')">英超 2023/24（曼城四连冠）</div>
  </div>

  {season_card("s1516", "英超 2015/16 —— 莱斯特城奇迹赛季", "380 场完整赛季 · 含逐事件数据（球员分析）")}
  {season_card("s2324", "英超 2023/24 —— 曼城四连冠赛季", "380 场完整赛季 · 比分数据")}
  {player_html}

  <div class="predictor">
    <h3>🎯 即时比分预测（2026 赛季 + 欧冠 + 五大联赛，任意球队）</h3>
    <div class="prow">
      <select id="ds">{league_html}</select>
      <select id="home"></select><span>主场 vs 客场</span><select id="away"></select>
      <button onclick="predict()">预测</button>
    </div>
    <div class="pout" id="pout"></div>
  </div>

  <footer>足球分析模型 · 数据仅供学习研究 · 跨联赛预测为 Elo 近似参考</footer>
</div>

<script>
const P = {json.dumps(js_params, ensure_ascii=False)};
const HT_RATIO = {ht_ratio:.3f};
const ODDS_MAP = {odds_map_json};
const ODDS_LIST = {odds_list_json};
// 球队中文名映射（显示用；逻辑仍用英文队名）
const CN = {cn_json};
const cn = t => CN[t] || t;

// 球队 -> 联赛 key（同名队可能出现在多个联赛，取其一；联赛筛选时用该联赛自身列表）
const LEAGUE_OF = {{}};
for (const k in P) for (const t in P[k].att) LEAGUE_OF[t] = k;
const LEAGUE_NAME = {{}};
for (const k in P) LEAGUE_NAME[k] = P[k].league;
const LEAGUE_ORDER = {league_order_json};

function allTeams() {{
  const arr = Object.keys(LEAGUE_OF);
  return arr.sort((a, b) => {{
    const la_ = LEAGUE_ORDER.indexOf(LEAGUE_OF[a]), lb_ = LEAGUE_ORDER.indexOf(LEAGUE_OF[b]);
    return (la_ - lb_) || a.localeCompare(b);
  }});
}}

function checkOddsServer() {{
  const el = document.getElementById('oddsStatus');
  if (!el) return;
  fetch('http://127.0.0.1:8765/ping', {{ mode: 'no-cors' }}).then(() => {{
    el.textContent = '盘口服务：已连接 ✓（抓取真实赔率可用）';
    el.className = 'ok';
  }}).catch(() => {{
    el.textContent = '盘口服务：未启动 — 请运行 python odds_server.py 后刷新';
    el.className = 'bad';
  }});
}}
function init() {{
  document.getElementById('ds').value = 'cl2627';
  fillTeams();
  document.getElementById('ds').onchange = fillTeams;
  predict();
  checkOddsServer();
}}
function fillTeams() {{
  const ds = document.getElementById('ds').value;
  let ts;
  if (ds === 'ALL') {{
    ts = allTeams();
  }} else {{
    ts = Object.keys(P[ds].att).sort();
  }}
  const h = document.getElementById('home'), a = document.getElementById('away');
  const curH = h.value, curA = a.value;
  h.innerHTML = ''; a.innerHTML = '';
  ts.forEach(t => {{
    h.add(new Option(cn(t), t)); a.add(new Option(cn(t), t));
  }});
  if (ts.indexOf(curH) >= 0) h.value = curH;
  if (ts.indexOf(curA) >= 0) a.value = curA;
  if (!h.value) h.selectedIndex = 0;
  if (!a.value) a.selectedIndex = (ts.length > 1) ? 1 : 0;
  predict();
}}
function fact(n) {{ let r = 1; for (let i = 2; i <= n; i++) r *= i; return r; }}
function pois(l, k) {{ return Math.exp(-l) * Math.pow(l, k) / fact(k); }}
function bar(v) {{ return '<span class="bar"><i style="width:' + Math.round(v * 100) + '%"></i></span>'; }}
const goalStats = (lamH, lamA) => {{
    const dist = new Array(17).fill(0);
    for (let i = 0; i <= 8; i++) for (let j = 0; j <= 8; j++) {{
      dist[i + j] += pois(lamH, i) * pois(lamA, j);
    }}
    const tot = dist.reduce((a, b) => a + b, 0);
    const p = dist.map(x => x / tot);
    let over15 = 0, over25 = 0, over35 = 0, under25 = 0;
    for (let k = 0; k <= 16; k++) {{
      if (k >= 2) over15 += p[k];
      if (k >= 3) over25 += p[k];
      if (k >= 4) over35 += p[k];
      if (k <= 2) under25 += p[k];
    }}
    let bi = 0;
    for (let k = 1; k <= 16; k++) if (p[k] > p[bi]) bi = k;
    return {{ p, over15, over25, over35, under25, best: bi, exp: lamH + lamA }};
  }};
  const goalHTML = (g) => {{
    const disp = g.p.slice(0, 6);
    disp[5] += g.p.slice(6).reduce((a, b) => a + b, 0);
    const mx = Math.max.apply(null, disp);
    const bars = disp.map((x, k) => {{
      const h = Math.max(2, Math.round(x / mx * 52));
      return '<div style="flex:1;text-align:center">' +
        '<div style="background:#2e86ab;height:' + h + 'px;margin:0 auto;width:72%"></div>' +
        '<div style="font-size:11px;color:#94a3b8">' + (k === 5 ? '6+' : k) + '</div>' +
        '<div style="font-size:11px;color:#cbd5e1">' + (x * 100).toFixed(1) + '%</div></div>';
    }}).join('');
    return '<div style="margin-top:8px;border-top:1px dashed #334155;padding-top:8px">' +
      '<b>总进球数预测</b>（模型估算，非盘口）：最可能 <b>' + g.best + ' 球</b>（' +
      (g.p[g.best] * 100).toFixed(1) + '%）｜ 期望总进球 <b>' + g.exp.toFixed(2) + '</b><br>' +
      '<div style="margin-top:4px">小球 ≤2 球 ' + (g.under25 * 100).toFixed(1) +
      '% ｜ 大 2.5 球 ' + (g.over25 * 100).toFixed(1) + '% ｜ 大 3.5 球 ' +
      (g.over35 * 100).toFixed(1) + '% ｜ 大 1.5 球 ' + (g.over15 * 100).toFixed(1) + '%</div>' +
      '<div style="display:flex;align-items:flex-end;margin-top:6px">' + bars + '</div>' +
      '<div class="dim" style="margin-top:2px">总进球分布（0-6+ 球，泊松模型）</div></div>';
  }};
const HT_LABEL = {{'W': '主胜', 'D': '平', 'L': '客胜'}};
const htftStats = (lamH, lamA) => {{
  const r = HT_RATIO;
  const lh1 = lamH * r, la1 = lamA * r;
  const lh2 = lamH * (1 - r), la2 = lamA * (1 - r);
  const grid = {{}};
  const res = (a, b) => a > b ? 'W' : (a === b ? 'D' : 'L');
  for (let i = 0; i <= 6; i++) for (let j = 0; j <= 6; j++) {{
    const pht = pois(lh1, i) * pois(la1, j);
    for (let k = 0; k <= 6; k++) for (let l = 0; l <= 6; l++) {{
      const p = pht * pois(lh2, k) * pois(la2, l);
      const key = res(i, j) + res(i + k, j + l);
      grid[key] = (grid[key] || 0) + p;
    }}
  }}
  const order = ['WW', 'WD', 'WL', 'DW', 'DD', 'DL', 'LW', 'LD', 'LL'];
  return order.map(k => [k, grid[k] || 0]).sort((a, b) => b[1] - a[1]);
}};
const htftHTML = (list) => {{
  const top3 = list.slice(0, 3);
  const cells = list.map((x, idx) => {{
    const hl = idx < 3;
    return '<div style="flex:1;min-width:64px;text-align:center;border:1px solid ' +
      (hl ? '#2e86ab' : '#334155') + ';border-radius:8px;padding:4px 2px;background:#0f172a">' +
      '<div style="font-size:12px;color:' + (x[0][0] === x[0][1] ? '#4ade80' : '#e2e8f0') + '">' +
      HT_LABEL[x[0][0]] + HT_LABEL[x[0][1]] + '</div>' +
      '<div style="font-size:11px;color:#94a3b8">' + (x[1] * 100).toFixed(1) + '%</div></div>';
  }}).join('');
  return '<div style="margin-top:8px;border-top:1px dashed #334155;padding-top:8px">' +
    '<b>半全场预测</b>（上半场+全场，模型拆分，非官方盘口）：最可能 <b>' +
    HT_LABEL[top3[0][0][0]] + HT_LABEL[top3[0][0][1]] + '</b>（' + (top3[0][1] * 100).toFixed(1) + '%）｜ 其他：' +
    top3.slice(1).map(t => HT_LABEL[t[0][0]] + HT_LABEL[t[0][1]] + '(' + (t[1] * 100).toFixed(1) + '%)').join('，') +
    '</div><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px">' + cells + '</div>' +
    '<div class="dim" style="margin-top:2px">半全场九宫格：前半场 后全场（如"平胜"=半场平、全场胜）；上半场进球占比 ' +
    (HT_RATIO * 100).toFixed(0) + '%（全部历史数据统计）</div></div>';
}};

function predict() {{
  const home = document.getElementById('home').value;
  const away = document.getElementById('away').value;
  const ds = document.getElementById('ds').value;
  if (!home || !away) return;
  let lh, la;
  if (ds !== 'ALL') {{ lh = ds; la = ds; }} else {{ lh = LEAGUE_OF[home]; la = LEAGUE_OF[away]; }}
  const tagSame = '<span class="tag same">同联赛 · 泊松精确预测</span>';
  const tagCross = '<span class="tag cross">跨联赛 · Elo 近似参考</span>';
  const box = (t) => t === 'W' ? '<b style="color:#4ade80">胜</b>' : (t === 'D' ? '<b style="color:#eab308">平</b>' : '<b style="color:#f87171">负</b>');
  const formLine = (f) => f ? f.split('').map(box).join(' ') : '<span class="dim">暂无数据</span>';
    const oddsPanel = '<div style="margin-top:10px;border-top:1px dashed #334155;padding-top:8px">' +
    '<div class="dim">盘口融合：一键抓取竞彩真实欧赔，或手动填写（含抽水自动去水），与模型概率加权平均</div>' +
    '<button onclick="fetchOdds()" style="padding:4px 12px;margin-bottom:6px">⚡ 抓取真实赔率</button> ' +
    '<input id="oh" type="number" min="1.01" step="0.01" placeholder="主胜赔率" style="width:88px"> ' +
    '<input id="od" type="number" min="1.01" step="0.01" placeholder="平赔" style="width:70px"> ' +
    '<input id="oa" type="number" min="1.01" step="0.01" placeholder="客胜赔率" style="width:88px"> ' +
    '<button onclick="calcOdds()" style="padding:4px 10px">融合计算</button> ' +
    '<select id="ow" style="width:118px;padding:4px"><option value="0.5">模型50%+市场50%</option>' +
    '<option value="0.3">模型30%+市场70%</option><option value="0.7">模型70%+市场30%</option></select>' +
    '<div id="mixout" style="margin-top:4px"></div></div>';

  if (lh === la) {{
    const p = P[lh];
    let lamH = Math.exp(p.mu + p.home_adv + p.att[home] - p.deff[away]);
    let lamA = Math.exp(p.mu - p.home_adv + p.att[away] - p.deff[home]);
    let ph = 0, pd = 0, pa = 0, best = null, top = [];
    for (let i = 0; i <= 8; i++) for (let j = 0; j <= 8; j++) {{
      const pr = pois(lamH, i) * pois(lamA, j);
      if (i > j) ph += pr; else if (i === j) pd += pr; else pa += pr;
      top.push({{s: i + '-' + j, p: pr}});
      if (!best || pr > best.p) best = {{s: i + '-' + j, p: pr}};
    }}
    const tot = ph + pd + pa;
    const g = goalStats(lamH, lamA);
    const ht = htftStats(lamH, lamA);
    top.sort((x, y) => y.p - x.p);
    const other = top.slice(1, 4).map(t => t.s + '(' + (t.p / tot * 100).toFixed(1) + '%)').join('，');
    last = {{home: home, away: away, lh: lh, mode: 'poisson', lamH: lamH, lamA: lamA,
             ph: ph / tot, pd: pd / tot, pa: pa / tot,
             formH: p.form[home] || '', formA: p.form[away] || '',
             formSrcH: (typeof p.form_src === 'object') ? (p.form_src[home] || '') : (p.form_src || ''),
             formSrcA: (typeof p.form_src === 'object') ? (p.form_src[away] || '') : (p.form_src || '')}};
    const om = ODDS_MAP[home + '|' + away];
    let oddsMatchBlock;
    if (om && om.h) {{
      oddsMatchBlock = '<div style="margin-top:10px;border:1px solid #22c55e;border-radius:10px;padding:8px 10px;background:rgba(34,197,94,.08)">' +
        '<b>🎯 竞彩真实盘口已匹配</b>（' + om.league + ' ' + (om.date || '') + ' ' + (om.time || '') + '）<br>' +
        cn(home) + ' 胜 <b style="color:#4ade80">' + om.h + '</b> ｜ 平 <b style="color:#eab308">' + om.d + '</b> ｜ ' + cn(away) + ' 胜 <b style="color:#f87171">' + om.a + '</b>' +
        '<div class="dim">' + om.src + '</div>' +
        '<button onclick="fillOdds()" style="padding:4px 12px;margin-top:4px">填入融合计算</button></div>';
    }} else {{
      oddsMatchBlock = '<div style="margin-top:10px;border:1px dashed #334155;border-radius:10px;padding:8px 10px">' +
        '<div class="dim">竞彩盘口：该场暂未匹配到报告球队（或未开售）。' +
        (ODDS_LIST.length ? '竞彩当前共 <b>' + ODDS_LIST.length + '</b> 场（含待开售）：<a href="#" onclick="toggleOddsList();return false">展开列表</a>' : '') + '</div>' +
        '<div id="oddslist" style="display:none;margin-top:6px">' + oddsListHTML() + '</div></div>';
    }}
    document.getElementById('pout').innerHTML =
      tagSame +
      '<div><b>' + cn(home) + '</b> 主场 vs <b>' + cn(away) + '</b>（' + p.season + '）</div>' +
      '<div style="margin-top:6px">预期进球：' + cn(home) + ' λ=' + lamH.toFixed(2) +
        ' ｜ ' + cn(away) + ' λ=' + lamA.toFixed(2) + '</div>' +
      '<div style="margin-top:6px">近5场状态（' + (last.formSrcH || '数据来源') + '）：' + cn(home) + ' ' + formLine(last.formH) +
        '　' + cn(away) + ' ' + formLine(last.formA) + '</div>' +
      '<div style="margin-top:6px">' + cn(home) + ' 胜 ' + (ph / tot * 100).toFixed(1) + '% ' + bar(ph / tot) +
        '　平局 ' + (pd / tot * 100).toFixed(1) + '% ' + bar(pd / tot) +
        '　' + cn(away) + ' 胜 ' + (pa / tot * 100).toFixed(1) + '% ' + bar(pa / tot) + '</div>' +
      '<div style="margin-top:6px">最可能比分：<b>' + best.s + '</b>（' + (best.p / tot * 100).toFixed(1) + '%）　其他：' + other + '</div>' +
      goalHTML(g) + htftHTML(ht) +
      oddsMatchBlock +
      oddsPanel +
      '<div style="margin-top:8px;border-top:1px dashed #334155;padding-top:8px">' +
      '<div class="dim">伤停修正（可选）：输入各队缺阵主力数（0-5），每缺 1 人攻防 -4%（经验系数）</div>' +
      cn(home) + ' 缺阵主力 <input id="nh" type="number" min="0" max="5" value="0" style="width:46px">　' +
      cn(away) + ' 缺阵主力 <input id="na" type="number" min="0" max="5" value="0" style="width:46px"> ' +
      '<button onclick="applyInj()" style="padding:4px 10px">修正计算</button>' +
      '<div id="injout" style="margin-top:4px"></div></div>';
  }} else {{
    const p1 = P[lh], p2 = P[la];
    const eloH = p1.elo[home] || 1500, eloA = p2.elo[away] || 1500;
    const adv = 100;
    const eh = 1 / (1 + Math.pow(10, (eloA - eloH - adv) / 400));
    const drawRate = 0.26;
    const ph = Math.max(0.05, Math.min(0.85, eh));
    const pa = Math.max(0.05, Math.min(0.85, 1 - eh - drawRate / 2));
    const pd = 1 - ph - pa;
    last = {{home: home, away: away, mode: 'elo', ph: ph, pd: pd, pa: pa}};
    const om2 = ODDS_MAP[home + '|' + away];
    let oddsMatchBlock;
    if (om2 && om2.h) {{
      oddsMatchBlock = '<div style="margin-top:10px;border:1px solid #22c55e;border-radius:10px;padding:8px 10px;background:rgba(34,197,94,.08)">' +
        '<b>🎯 竞彩真实盘口已匹配</b>（' + om2.league + ' ' + (om2.date || '') + ' ' + (om2.time || '') + '）<br>' +
        cn(home) + ' 胜 <b style="color:#4ade80">' + om2.h + '</b> ｜ 平 <b style="color:#eab308">' + om2.d + '</b> ｜ ' + cn(away) + ' 胜 <b style="color:#f87171">' + om2.a + '</b>' +
        '<div class="dim">' + om2.src + '</div>' +
        '<button onclick="fillOdds()" style="padding:4px 12px;margin-top:4px">填入融合计算</button></div>';
    }} else {{
      oddsMatchBlock = '<div style="margin-top:10px;border:1px dashed #334155;border-radius:10px;padding:8px 10px">' +
        '<div class="dim">竞彩盘口：该场暂未匹配到报告球队（或未开售）。' +
        (ODDS_LIST.length ? '竞彩当前共 <b>' + ODDS_LIST.length + '</b> 场（含待开售）：<a href="#" onclick="toggleOddsList();return false">展开列表</a>' : '') + '</div>' +
        '<div id="oddslist" style="display:none;margin-top:6px">' + oddsListHTML() + '</div></div>';
    }}
    document.getElementById('pout').innerHTML =
      tagCross +
      '<div><b>' + cn(home) + '</b> 主场 vs <b>' + cn(away) + '</b>（' + p1.season + ' vs ' + p2.season + '）</div>' +
      '<div style="margin-top:6px">实力评级（Elo）：' + cn(home) + ' ' + eloH + ' ｜ ' + cn(away) + ' ' + eloA + '</div>' +
      '<div style="margin-top:6px">' + cn(home) + ' 胜 ' + (ph * 100).toFixed(1) + '% ' + bar(ph) +
        '　平局 ' + (pd * 100).toFixed(1) + '% ' + bar(pd) +
        '　' + cn(away) + ' 胜 ' + (pa * 100).toFixed(1) + '% ' + bar(pa) + '</div>' +
      '<div class="dim" style="margin-top:4px">两队不在同一联赛，无直接交锋数据；此结果基于 Elo 评级近似，仅供参考。</div>' +
      oddsMatchBlock +
      oddsPanel;
  }}
}}
var last = null;
function oddsListHTML() {{
  if (!ODDS_LIST.length) return '<span class="dim">暂无在售场次</span>';
  const rows = ODDS_LIST.map(function(m) {{
    let odds;
    if (m.h && m.d && m.a) odds = m.h + ' / ' + m.d + ' / ' + m.a;
    else if (m.hh && m.hd && m.ha) odds = '<span class="dim">让球盘 ' + m.hh + ' / ' + m.hd + ' / ' + m.ha + (m.gl ? '（' + m.gl + '）' : '') + '</span>';
    else odds = '<span class="dim">—</span>';
    const st = (m.st === 'Selling') ? '<span style="color:#4ade80">在售</span>' : '<span class="dim">待开售</span>';
    return '<div style="padding:2px 0">' + (m.num ? '<b>' + m.num + '</b> ' : '') + m.lg + '：' + m.hn + ' vs ' + m.an + '　欧赔 ' + odds + '　' + st + '</div>';
  }}).join('');
  return '<div style="max-height:190px;overflow:auto;border:1px solid #334155;border-radius:8px;padding:6px 10px;background:rgba(15,23,42,.6)">' + rows + '</div>';
}}
function toggleOddsList() {{
  const el = document.getElementById('oddslist');
  if (el) el.style.display = (el.style.display === 'none') ? 'block' : 'none';
}}
function fillOdds() {{
  if (!last) return;
  const om = ODDS_MAP[last.home + '|' + last.away];
  if (!om || !om.h) return;
  document.getElementById('oh').value = om.h;
  document.getElementById('od').value = om.d;
  document.getElementById('oa').value = om.a;
  calcOdds();
}}
function fetchOdds() {{
  if (!last) return;
  const out = document.getElementById('mixout');
  out.innerHTML = '<span class="dim">正在连接本地盘口服务（127.0.0.1:8765）…</span>';
  const url = 'http://127.0.0.1:8765/odds?home=' + encodeURIComponent(cn(last.home)) + '&away=' + encodeURIComponent(cn(last.away));
  fetch(url).then(r => r.json()).then(j => {{
    if (!j.found) {{
      out.innerHTML = '<span class="dim">未找到该场比赛：' + (j.msg || '') + '。竞彩在售场次示例：' + ((j.available || []).join('；') || '无') + '（一般赛前 1-3 天开售）</span>';
      return;
    }}
    const oh = document.getElementById('oh'), od = document.getElementById('od'), oa = document.getElementById('oa');
    oh.value = j.odds.h; od.value = j.odds.d; oa.value = j.odds.a;
    out.innerHTML = '<span class="dim">已获取真实赔率：' + j.league + ' ' + j.home + ' 胜 ' + j.odds.h + ' / 平 ' + j.odds.d + ' / ' + j.away + ' 胜 ' + j.odds.a + '（' + j.source + '）' + (j.note ? '；' + j.note : '') + '</span>';
    calcOdds();
  }}).catch(e => {{
    out.innerHTML = '<span class="dim">连接失败：请先运行 python odds_server.py 启动本地盘口服务（保持窗口开着），再点抓取。</span>';
  }});
}}
function calcOdds() {{
  if (!last) return;
  const oh = parseFloat(document.getElementById('oh').value);
  const od = parseFloat(document.getElementById('od').value);
  const oa = parseFloat(document.getElementById('oa').value);
  const w = parseFloat(document.getElementById('ow').value);
  const out = document.getElementById('mixout');
  if (!(oh > 1) || !(od > 1) || !(oa > 1)) {{ out.innerHTML = '<span class="dim">请填写完整的三项欧赔（均需大于 1）。</span>'; return; }}
  let mh = 1 / oh, md = 1 / od, ma = 1 / oa;
  const msum = mh + md + ma;
  mh /= msum; md /= msum; ma /= msum;
  const fh = w * last.ph + (1 - w) * mh;
  const fd = w * last.pd + (1 - w) * md;
  const fa = w * last.pa + (1 - w) * ma;
  const names = [cn(last.home) + '胜', '平局', cn(last.away) + '胜'];
  const fv = [fh, fd, fa];
  let bi = 0; for (let i = 1; i < 3; i++) if (fv[i] > fv[bi]) bi = i;
  out.innerHTML =
    '<div style="margin-top:2px">市场隐含概率（去水）：' + names[0] + ' ' + (mh * 100).toFixed(1) + '%　平 ' + (md * 100).toFixed(1) + '%　' + names[2] + ' ' + (ma * 100).toFixed(1) + '%</div>' +
    '<div>融合概率：' + names[0] + ' <b>' + (fh * 100).toFixed(1) + '%</b>　平 ' + (fd * 100).toFixed(1) + '%　' + names[2] + ' <b>' + (fa * 100).toFixed(1) + '%</b></div>' +
    '<div style="color:#7dd3fc">融合推荐：<b>' + names[bi] + '</b>（' + (fv[bi] * 100).toFixed(1) + '%）</div>' +
    '<div class="dim">赔率含抽水已归一化；融合 = 模型×' + (w * 100) + '% + 市场×' + ((1 - w) * 100) + '%</div>';
}}
function applyInj() {{
  if (!last || last.mode !== 'poisson') return;
  const nh = parseInt(document.getElementById('nh').value || '0', 10);
  const na = parseInt(document.getElementById('na').value || '0', 10);
  const p = P[last.lh];
  const k = 0.96;
  const lamH = Math.exp(p.mu + p.home_adv + p.att[last.home] * Math.pow(k, nh) - p.deff[last.away] * Math.pow(k, na));
  const lamA = Math.exp(p.mu - p.home_adv + p.att[last.away] * Math.pow(k, na) - p.deff[last.home] * Math.pow(k, nh));
  let ph = 0, pd = 0, pa = 0, best = null;
  for (let i = 0; i <= 8; i++) for (let j = 0; j <= 8; j++) {{
    const pr = pois(lamH, i) * pois(lamA, j);
    if (i > j) ph += pr; else if (i === j) pd += pr; else pa += pr;
    if (!best || pr > best.p) best = {{s: i + '-' + j, p: pr}};
  }}
  const tot = ph + pd + pa;
  const g = goalStats(lamH, lamA);
  const ht = htftStats(lamH, lamA);
  document.getElementById('injout').innerHTML =
    '<div style="margin-top:2px">修正后预期进球：' + cn(last.home) + ' λ=' + lamH.toFixed(2) + ' ｜ ' + cn(last.away) + ' λ=' + lamA.toFixed(2) + '</div>' +
    '<div>修正后：' + cn(last.home) + ' 胜 ' + (ph / tot * 100).toFixed(1) + '%　平 ' + (pd / tot * 100).toFixed(1) + '%　' + cn(last.away) + ' 胜 ' + (pa / tot * 100).toFixed(1) + '%　最可能 <b>' + best.s + '</b></div>' +
    '<div>修正后总进球：最可能 <b>' + g.best + ' 球</b>（' + (g.p[g.best] * 100).toFixed(1) + '%）｜ 大 2.5 球 ' + (g.over25 * 100).toFixed(1) + '% ｜ 小球 ≤2 ' + (g.under25 * 100).toFixed(1) + '%</div>' +
    htftHTML(ht) +
    '<div class="dim">每缺 1 名主力攻防 -4%（经验系数）；比赛前请以官方大名单为准。</div>';
}}

function show(id) {{
  document.querySelectorAll('.season').forEach(s => s.classList.remove('show'));
  document.getElementById(id).classList.add('show');
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
}}
window.onload = init;
</script>
</body>
</html>"""


if __name__ == "__main__":
    build()
