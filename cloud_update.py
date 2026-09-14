# -*- coding: utf-8 -*-
"""云端自动更新（GitHub Actions 兜底）：openfootball 源合并 -> 生成报告 -> 更新 index.html
电脑关机时也能运行。只增不减：本地已有数据（含人工核实补录）一律保留。
用法: python cloud_update.py [--dry-run]
"""
import json, os, sys, shutil, subprocess, urllib.request, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "football_data")
MODEL = os.path.join(ROOT, "football_model")
INDEX = os.path.join(ROOT, "index.html")

DRY = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

# 2026/27 当前赛季可自动更新的联赛（openfootball 源）
SRC = {
    "openfootball_2026-27_en.1.json": "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/en.1.json",
    "openfootball_2026-27_es.1.json": "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/es.1.json",
    "openfootball_2026-27_de.1.json": "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/de.1.json",
    "openfootball_2026-27_it.1.json": "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/it.1.json",
    "openfootball_2026-27_fr.1.json": "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/fr.1.json",
    "openfootball_2026-27_pt.1.json": "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/pt.1.json",
    "openfootball_2026-27_nl.1.json": "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/nl.1.json",
}

def norm(s):
    return (s or "").strip()

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def merge_matches(local_matches, new_matches):
    """只增不减：返回 (新列表, 新增数, 补分数组)"""
    by_key = {}
    for i, m in enumerate(local_matches):
        by_key[(m.get("date"), norm(m.get("team1")), norm(m.get("team2")))] = i
    added = []
    filled = 0
    for nm in new_matches:
        k = (nm.get("date"), norm(nm.get("team1")), norm(nm.get("team2")))
        if k in by_key:
            lm = local_matches[by_key[k]]
            if not lm.get("score") and nm.get("score"):
                lm["score"] = nm["score"]
                filled += 1
        else:
            added.append(nm)
    if not added:
        return local_matches, 0, filled
    # 按 round 分组新增
    added_by_round = {}
    order = []
    for m in added:
        r = m.get("round", "")
        if r not in added_by_round:
            added_by_round[r] = []
            order.append(r)
        added_by_round[r].append(m)
    # 本地 round 顺序
    local_rounds = []
    for m in local_matches:
        r = m.get("round", "")
        if r not in local_rounds:
            local_rounds.append(r)
    result = []
    done = set()
    for r in local_rounds:
        result += [m for m in local_matches if m.get("round") == r]
        if r in added_by_round:
            result += added_by_round[r]
            done.add(r)
    for r in order:
        if r not in done:
            result += added_by_round[r]
    return result, len(added), filled

def main():
    total_add = 0
    total_fill = 0
    changed = 0
    for fname, url in SRC.items():
        fp = os.path.join(DATA, fname)
        if not os.path.exists(fp):
            print("!! 本地缺数据文件:", fname); continue
        try:
            new = fetch(url)
        except Exception as e:
            print("!! 下载失败 %s: %s" % (fname, e)); continue
        with open(fp, "r", encoding="utf-8") as f:
            local = json.load(f)
        new_matches = new.get("matches", [])
        local_matches = local.get("matches", [])
        merged, n_add, n_fill = merge_matches(local_matches, new_matches)
        if n_add or n_fill:
            out = dict(local)
            out["matches"] = merged
            txt = json.dumps(out, ensure_ascii=False, indent=1)
            with open(fp, "r", encoding="utf-8") as f:
                old_txt = f.read()
            if txt != old_txt:
                changed += 1
                if not DRY:
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(txt)
            print("%s: 新增 %d 场, 补分 %d 场" % (fname, n_add, n_fill))
            total_add += n_add
            total_fill += n_fill
    print("合计: 新增 %d 场, 补分 %d 场, 改写文件 %d 个" % (total_add, total_fill, changed))
    if DRY:
        print("(dry-run 模式，未写文件、未生成报告)")
        return 0
    if not (total_add or total_fill) and not FORCE:
        print("无数据变化，跳过重新生成")
        return 0
    # 重新生成报告
    print("== 重新生成报告 ==")
    r = subprocess.run([sys.executable, os.path.join(MODEL, "generate_report.py")],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    print(r.stdout[-800:])
    if r.returncode != 0:
        print("!! 生成报告失败:", r.stderr[-500:])
        return 1
    rep = os.path.join(MODEL, "football_analysis_report.html")
    if os.path.exists(rep):
        shutil.copy(rep, INDEX)
        print("已更新 index.html: %d bytes" % os.path.getsize(INDEX))
    else:
        print("!! 报告文件不存在:", rep); return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
