# -*- coding: utf-8 -*-
"""
足球分析 · 本地盘口服务（真实赔率自动抓取）
==========================================
数据源：中国竞彩网官方接口（webapi.sporttery.cn，公开可访问）
用法：python odds_server.py
  启动后保持窗口运行，然后在足球分析报告.html 里选队预测，
  点击"抓取真实赔率"按钮即可自动填入竞彩欧赔并完成融合计算。

说明：竞彩赔率 = 官方固定奖金（含返还），即标准欧赔；
      报告中融合计算会自动去水（归一化）。
"""
import http.server
import json
import urllib.request
import urllib.parse
import sys

# 竞彩官方统一接口（覆盖全部在售/待售场次，含各联赛；旧 getMatchCalculatorV1 已被 WAF 拦截）
API_URL = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchListV1.qry?clientCode=3001"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.sporttery.cn/jc/zqszsc/index.html",
}
PORT = 8765

# 竞彩队名（或报告中可能用到的别名）→ 报告中中文名
ALIAS = {
    "莱红牛": "莱比锡", "莱比锡红牛": "莱比锡", "RB莱比锡": "莱比锡",
    "萨巴赫": "沙巴巴库", "巴库": "沙巴巴库",
    "矿工": "顿涅茨克矿工", "沙克塔": "顿涅茨克矿工",
    "萨尔茨堡": "萨尔茨堡红牛",
    "博德闪耀": "博德闪耀", "闪耀哥": "博德闪耀",
    "奥林匹亚": "奥林匹亚科斯",
    "布鲁日": "布鲁日", "斯拉维亚": "布拉格斯拉维亚", "斯莱维亚": "布拉格斯拉维亚",
    "朗斯": "朗斯", "兰斯": "兰斯",
    "科莫": "科莫", "莱比锡": "莱比锡",
    "费内巴切": "费内巴切", "费内巴": "费内巴切",
    "罗马": "罗马", "曼联": "曼联", "曼彻斯特联": "曼联",
    "拜仁": "拜仁慕尼黑", "拜仁慕尼黑": "拜仁慕尼黑",
    "埃因霍温": "埃因霍温", "PSV": "埃因霍温",
    "阿森纳": "阿森纳", "那不勒斯": "那不勒斯", "国际米兰": "国际米兰", "国米": "国际米兰",
    "皇家马德里": "皇家马德里", "皇马": "皇家马德里",
    "巴塞罗那": "巴塞罗那", "巴萨": "巴塞罗那",
    "利物浦": "利物浦", "曼城": "曼城", "曼彻斯特城": "曼城",
    "多特蒙德": "多特蒙德", "斯图加特": "斯图加特", "勒沃库森": "勒沃库森",
    "巴黎圣日耳曼": "巴黎圣日耳曼", "巴黎": "巴黎圣日耳曼",
    "摩纳哥": "摩纳哥", "里尔": "里尔", "马赛": "马赛", "尼斯": "尼斯",
    "尤文图斯": "尤文图斯", "尤文": "尤文图斯", "AC米兰": "AC米兰", "ac米兰": "AC米兰",
    "亚特兰大": "亚特兰大", "拉齐奥": "拉齐奥", "佛罗伦萨": "佛罗伦萨", "都灵": "都灵",
    "波尔图": "波尔图", "本菲卡": "本菲卡", "葡萄牙体育": "葡萄牙体育",
    "阿贾克斯": "阿贾克斯", "费耶诺德": "费耶诺德", "阿尔克马尔": "阿尔克马尔",
    "亨克": "亨克", "安特卫普": "安特卫普", "根特": "根特",
    "加拉塔萨雷": "加拉塔萨雷", "贝西克塔斯": "贝西克塔斯", "特拉布宗": "特拉布宗体育",
    "凯尔特人": "凯尔特人", "流浪者": "流浪者",
    "布拉迪斯拉发": "布拉迪斯拉发", "斯洛万": "布拉迪斯拉发",
    "维京": "维京", "维京人": "维京",
    "雅典AEK": "雅典AEK", "AEK雅典": "雅典AEK",
    "林茨": "林茨", "LASK": "林茨",
    # 竞彩常见简称（2026/27 在售场次）
    "米堡": "米德尔斯堡", "马竞": "马德里竞技",
    "阿尔克马": "阿尔克马尔", "格风暴": "格拉茨风暴",
    "奈梅亨": "尼美根", "拉科": "拉科鲁尼亚",
    "桑坦德": "桑坦德竞技", "伊普斯": "伊普斯维奇",
    "大田市民": "大田韩亚", "赫塔费": "赫塔菲", "巴伦西亚": "瓦伦西亚",
}


def fetch_matches():
    """拉取竞彩全部在售/待售比赛列表（含欧赔）"""
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode("utf-8"))
    value = j.get("value", {})
    last_upd = value.get("lastUpdateTime", "")  # 形如 2026-09-15 08:49:05
    upd_date = last_upd.split(" ")[0] if last_upd else ""
    upd_time = last_upd.split(" ")[1] if " " in last_upd else ""
    out = []
    for day in value.get("matchInfoList", []):
        for m in day.get("subMatchList", []):
            ol = {o.get("poolCode"): o for o in (m.get("oddsList") or [])}
            had = ol.get("HAD") or {}
            hhad = ol.get("HHAD") or {}
            def _v(o, k):
                v = o.get(k)
                return v if v not in (None, "") else None
            # 有赔率 = 已开售；无赔率 = 待开售
            has_odds = _v(had, "h") is not None or _v(hhad, "h") is not None
            rec = {
                "matchId": m.get("matchId"),
                "matchNum": m.get("matchNumStr") or "",   # 如 周二001
                "home": m.get("homeTeamAbbName") or "",
                "away": m.get("awayTeamAbbName") or "",
                "league": m.get("leagueAbbName") or "",
                "leagueFull": m.get("leagueAllName") or "",
                "matchDate": m.get("matchDate") or "",
                "matchTime": m.get("matchTime") or "",
                "status": "Selling" if has_odds else "Define",
                "had": {"h": _v(had, "h"), "d": _v(had, "d"), "a": _v(had, "a")} if had else None,
                "hhad": {"h": _v(hhad, "h"), "d": _v(hhad, "d"), "a": _v(hhad, "a"),
                         "goalLine": hhad.get("goalLine") or ""} if hhad else None,
                "updateDate": upd_date,
                "updateTime": upd_time,
            }
            out.append(rec)
    return out


def norm(name):
    """归一化：去空格/横线，统一小写"""
    if not name:
        return ""
    n = name.strip().replace(" ", "").replace("-", "").replace("·", "").lower()
    return n


def name_match(jc_name, report_name):
    """竞彩名 vs 报告中中文名 匹配（双向别名 + 包含）"""
    if not jc_name or not report_name:
        return False
    jc = jc_name.strip()
    rp = report_name.strip()
    # 竞彩名自身 + 竞彩名的别名（如"莱红牛"→"莱比锡"）
    cands = {jc, ALIAS.get(jc, "")}
    cands.discard("")
    for c in cands:
        if not c:
            continue
        if c in rp or rp in c:
            return True
    # 报告名的别名（如"拜仁慕尼黑"→"拜仁"，检查竞彩名是否含"拜仁"）
    rp_alias = ALIAS.get(rp, "")
    if rp_alias and rp_alias != rp and (rp_alias in jc or jc in rp_alias):
        return True
    # 归一化匹配
    nj, nr = norm(jc), norm(rp)
    if nj and nr and (nj in nr or nr in nj or nj == nr):
        return True
    # 竞彩常用 2 字简称（如"拜仁"↔"拜仁慕尼黑"）
    if len(jc) == 2 and jc in rp:
        return True
    if len(rp) == 2 and rp in jc:
        return True
    return False


def find_match(home_cn, away_cn):
    try:
        ms = fetch_matches()
    except Exception as e:
        return None, f"抓取失败（网络/接口异常）：{type(e).__name__}", []
    for m in ms:
        if name_match(m["home"], home_cn) and name_match(m["away"], away_cn):
            return m, None, ms
    cands = []
    for m in ms:
        if name_match(m["home"], home_cn) or name_match(m["away"], away_cn):
            cands.append(f"{m['home']} vs {m['away']}（{m['league']}）")
    return None, "未找到该场比赛", cands


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        body = {}
        if parsed.path == "/ping":
            body = {"ok": True, "service": "odds-server", "port": PORT}
        elif parsed.path == "/today":
            try:
                ms = fetch_matches()
                body = {"count": len(ms),
                        "matches": [f"{m['home']} vs {m['away']}（{m['league']}）" for m in ms[:40]]}
            except Exception as e:
                body = {"count": 0, "msg": str(e)}
        else:
            home = qs.get("home", [""])[0]
            away = qs.get("away", [""])[0]
            if not home or not away:
                body = {"found": False, "msg": "缺少 home/away 参数"}
            else:
                m, err, cands = find_match(home, away)
                if m:
                    odds = m["had"] or m["hhad"] or {}
                    body = {
                        "found": True,
                        "home": m["home"], "away": m["away"],
                        "league": m["league"],
                        "matchDate": m["matchDate"], "matchTime": m["matchTime"],
                        "odds": {"h": odds.get("h"), "d": odds.get("d"), "a": odds.get("a")},
                        "source": f"中国竞彩网官方接口 更新 {m['updateDate']} {m['updateTime']}",
                        "note": "该场竞彩仅售让球玩法，赔率含让球盘" if not m["had"] else "",
                    }
                else:
                    body = {"found": False, "msg": err, "available": cands[:10]}
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def main():
    print("=" * 58)
    print("  足球分析 · 本地盘口服务  http://127.0.0.1:%d" % PORT)
    print("  数据源：中国竞彩网官方接口（实时欧赔）")
    try:
        ms = fetch_matches()
        print("  当前在售场次：%d 场" % len(ms))
    except Exception as e:
        print("  在售场次获取失败（不影响服务）：%s" % type(e).__name__)
    print("  保持此窗口运行，然后在报告中点『抓取真实赔率』")
    print("  关闭窗口 = 停止服务")
    print("=" * 58)
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        srv.serve_forever()
    except OSError as e:
        print(f"启动失败：{e}（端口被占用？先关闭其他实例）")
        sys.exit(1)


if __name__ == "__main__":
    main()
