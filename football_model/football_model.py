# -*- coding: utf-8 -*-
"""
足球分析模型（核心模块）
================================
数据：StatsBomb Open Data —— 英超 2015/16 完整赛季（380 场比赛）
功能：
  1) 比赛胜负 / 比分预测   —— 泊松回归（经典足球模型）+ 机器学习（GradientBoosting）双模型 + 回测对比
  2) 球队强弱评估         —— Elo 评级、攻防强度（泊松参数）、积分榜、攻防散点
  3) 球员表现分析         —— 进球/射门/xG/助攻/关键传球/扑救，90 分钟标准化 + 综合评分
依赖：pandas numpy scipy scikit-learn matplotlib

用法：直接 import 本模块调用各函数，或运行 run_analysis.py 一键产出全部分析与图表。
"""

import os
import json
import itertools
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from scipy.optimize import minimize
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# 全局配置
# ---------------------------------------------------------------------------
# 中文字体（Windows）
for _f in ["Microsoft YaHei", "SimHei", "SimSun"]:
    if any(_f == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [_f]
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 120

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "football_data")
EVENTS_DIR = os.path.join(DATA_DIR, "events")
CHART_DIR = os.path.join(BASE_DIR, "charts")
MATCHES_FILE = os.path.join(DATA_DIR, "m_2_27.json")   # 英超 2015/16

SEASON_NAME = "英超 2015/16"


# ---------------------------------------------------------------------------
# 1. 数据加载
# ---------------------------------------------------------------------------
def load_matches(matches_file=MATCHES_FILE):
    """从 StatsBomb matches JSON 构建比赛表。"""
    with open(matches_file, encoding="utf-8") as f:
        raw = json.load(f)
    rows = []
    for m in raw:
        rows.append({
            "match_id": m["match_id"],
            "date": pd.to_datetime(m["match_date"]),
            "week": m["match_week"],
            "home": m["home_team"]["home_team_name"],
            "away": m["away_team"]["away_team_name"],
            "home_goals": m["home_score"],
            "away_goals": m["away_score"],
            "stadium": (m.get("stadium") or {}).get("name", ""),
        })
    df = pd.DataFrame(rows).sort_values(["week", "date"]).reset_index(drop=True)
    # 结果标签：H / D / A
    df["result"] = np.select(
        [df.home_goals > df.away_goals, df.home_goals == df.away_goals],
        ["H", "D"], default="A")
    return df


def load_matches_openfootball(matches_file, season_name="", skip_unplayed=True):
    """
    从 openfootball/football.json 格式加载比赛表（如英超 2023/24）。
    该格式顶层为 {"name": ..., "matches": [...]}，每场含 team1/team2/score.ft/date。
    统一输出与 load_matches 相同的 DataFrame 结构。
    """
    with open(matches_file, encoding="utf-8") as f:
        raw = json.load(f)
    matches = raw.get("matches", [])
    # 按比赛日排序（"Matchday N" → N）
    def _week(s):
        if not s:
            return 0
        digits = "".join(ch for ch in str(s) if ch.isdigit())
        return int(digits) if digits else 0
    rows = []
    for i, m in enumerate(matches):
        score = m.get("score")
        if isinstance(score, dict):
            ft = score.get("ft") or [None, None]
        elif isinstance(score, (list, tuple)) and len(score) == 2:
            ft = list(score)
        else:
            ft = [None, None]
        if skip_unplayed and (ft[0] is None or ft[1] is None):
            continue
        rows.append({
            "match_id": m.get("id", i + 1),
            "date": pd.to_datetime(m.get("date"), errors="coerce"),
            "week": _week(m.get("round")),
            "home": m["team1"],
            "away": m["team2"],
            "home_goals": ft[0] if ft[0] is not None else 0,
            "away_goals": ft[1] if ft[1] is not None else 0,
            "stadium": "",
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(["week", "date"]).reset_index(drop=True)
    df["result"] = np.select(
        [df.home_goals > df.away_goals, df.home_goals == df.away_goals],
        ["H", "D"], default="A")
    if season_name:
        df.attrs["season_name"] = season_name
    return df


def load_matches_cl(matches_file, season_name="欧冠 2025/26", skip_unplayed=True):
    """
    从 openfootball/champions-league 的欧冠 JSON 加载比赛表。
    欧冠 round 为 "League Matchday 1" / "Playoffs Matchday 1" / "Finals Round of 16"
    等，需映射为顺序轮次（1-14），保证按比赛进程排序。
    """
    with open(matches_file, encoding="utf-8") as f:
        raw = json.load(f)
    matches = raw.get("matches", [])

    def _round_no(s):
        s = (s or "").lower()
        if "matchday" in s:
            n = "".join(ch for ch in s if ch.isdigit())
            base = 8 if "playoffs" in s else 0
            return base + (int(n) if n else 0)
        if "round of 16" in s:
            return 11
        if "quarter" in s:
            return 12
        if "semi" in s:
            return 13
        if "final" in s:
            return 14
        return 0

    rows = []
    for i, m in enumerate(matches):
        score = m.get("score") or {}
        ft = score.get("ft") or [None, None]
        if skip_unplayed and (ft[0] is None or ft[1] is None):
            continue
        rows.append({
            "match_id": m.get("id", i + 1),
            "date": pd.to_datetime(m.get("date"), errors="coerce"),
            "week": _round_no(m.get("round")),
            "home": m["team1"],
            "away": m["team2"],
            "home_goals": int(ft[0]) if ft[0] is not None else 0,
            "away_goals": int(ft[1]) if ft[1] is not None else 0,
            "stadium": "",
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(["week", "date"]).reset_index(drop=True)
    df["result"] = np.select(
        [df.home_goals > df.away_goals, df.home_goals == df.away_goals],
        ["H", "D"], default="A")
    if season_name:
        df.attrs["season_name"] = season_name
    return df


def load_matches_csv(matches_file, season_name=""):
    """
    从自定义 CSV 加载比赛表，列名需包含：
      date, home, away, home_goals(或 hg), away_goals(或 ag)
    可选列：week（轮次，默认按行序递增）。
    这是让用户接入自己数据（含新赛季）的通用入口。
    """
    df = pd.read_csv(matches_file)
    df.columns = [str(c).strip().lower() for c in df.columns]
    rename = {"hg": "home_goals", "ag": "away_goals",
              "date": "date", "home": "home", "away": "away"}
    for src, dst in rename.items():
        if src in df.columns and dst not in df.columns:
            df = df.rename(columns={src: dst})
    need = ["home", "away", "home_goals", "away_goals"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少必需列: {missing}（需要 home/away/home_goals/away_goals，可选 date/week）")
    if "date" not in df.columns:
        df["date"] = pd.Timestamp("2000-01-01")
    else:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "week" not in df.columns:
        df["week"] = range(1, len(df) + 1)
    df["match_id"] = range(1, len(df) + 1)
    df["stadium"] = ""
    df = df[["match_id", "date", "week", "home", "away",
             "home_goals", "away_goals", "stadium"]].copy()
    df["result"] = np.select(
        [df.home_goals > df.away_goals, df.home_goals == df.away_goals],
        ["H", "D"], default="A")
    if season_name:
        df.attrs["season_name"] = season_name
    return df


def load_events(match_id):
    """读取单场比赛事件数据（若本地存在）。"""
    fp = os.path.join(EVENTS_DIR, f"{match_id}.json")
    if not os.path.exists(fp):
        return None
    with open(fp, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. Elo 评级（球队强弱动态评估）
# ---------------------------------------------------------------------------
def compute_elo(matches, k=32, home_adv=100, initial=1500):
    """
    标准 Elo 评级：
      E_home = 1 / (1 + 10^((R_away - R_home) / 400))
      预期主场得分 Sp_home = E_home + 主场优势(以预期值形式加入)
      实际得分 S_home: 胜=1 平=0.5 负=0
      R_new = R_old + K * (S - Sp)
    返回：最终评级 + 逐场 Elo 序列（用于画曲线）
    """
    teams = sorted(set(matches.home) | set(matches.away))
    rating = {t: initial for t in teams}
    history = {t: [] for t in teams}
    weeks = {t: [] for t in teams}

    for _, row in matches.iterrows():
        h, a = row.home, row.away
        eh = 1 / (1 + 10 ** ((rating[a] - rating[h]) / 400))
        # 主场优势：把主场优势折算进预期得分
        sp_h = np.clip(eh + home_adv / 400.0, 0.01, 0.99)
        sp_a = 1 - sp_h
        sh = 1.0 if row.result == "H" else (0.5 if row.result == "D" else 0.0)
        sa = 1.0 - sh
        rating[h] += k * (sh - sp_h)
        rating[a] += k * (sa - sp_a)
        history[h].append(rating[h]); history[a].append(rating[a])
        weeks[h].append(row.week); weeks[a].append(row.week)

    elo_df = pd.DataFrame({
        "team": list(rating.keys()),
        "elo": [round(v) for v in rating.values()],
    }).sort_values("elo", ascending=False).reset_index(drop=True)
    return elo_df, history, weeks


# ---------------------------------------------------------------------------
# 3. 泊松回归模型（胜负/比分预测）
# ---------------------------------------------------------------------------
class PoissonModel:
    """
    经典足球比分模型：
      log(λ_home) = μ + α_home + att_home - def_away
      log(λ_away) = μ - α_home + att_away - def_home
    用最大似然估计球队攻防强度，再枚举比分矩阵得到胜/平/负概率。
    """

    def __init__(self):
        self.teams = None
        self.att_ = None
        self.def_ = None
        self.mu_ = None
        self.home_adv_ = None
        self.fit_ok_ = False

    def _neg_ll(self, theta, df):
        n_team = len(self.teams)
        mu, home_adv = theta[0], theta[1]
        att = theta[2:2 + n_team]
        deff = theta[2 + n_team:2 + 2 * n_team]
        idx = {t: i for i, t in enumerate(self.teams)}
        hg = df.home_goals.values.astype(float)
        ag = df.away_goals.values.astype(float)
        h_idx = df.home.map(idx).values
        a_idx = df.away.map(idx).values
        lam_h = np.exp(mu + home_adv + att[h_idx] - deff[a_idx])
        lam_a = np.exp(mu - home_adv + att[a_idx] - deff[h_idx])
        ll = np.sum(hg * np.log(lam_h) - lam_h - _log_fact(hg))
        ll += np.sum(ag * np.log(lam_a) - lam_a - _log_fact(ag))
        # 弱先验约束攻防均值≈0，保证可辨识
        ll -= 0.5 * (att.mean() ** 2 + deff.mean() ** 2) * len(df) / 10.0
        return -ll

    def fit(self, matches):
        self.teams = sorted(set(matches.home) | set(matches.away))
        n = len(self.teams)
        mu0 = np.log(np.mean(matches.home_goals + matches.away_goals))
        x0 = np.zeros(2 + 2 * n)
        x0[0] = mu0
        x0[1] = 0.3
        res = minimize(self._neg_ll, x0, args=(matches,), method="BFGS",
                       options={"maxiter": 5000})
        self.mu_, self.home_adv_ = res.x[0], res.x[1]
        self.att_ = dict(zip(self.teams, res.x[2:2 + n]))
        self.def_ = dict(zip(self.teams, res.x[2 + n:2 + 2 * n]))
        self.fit_ok_ = True
        return self

    def expected_goals(self, home, away):
        """返回 (λ_home, λ_away)"""
        lam_h = np.exp(self.mu_ + self.home_adv_ + self.att_[home] - self.def_[away])
        lam_a = np.exp(self.mu_ - self.home_adv_ + self.att_[away] - self.def_[home])
        return lam_h, lam_a

    def score_matrix(self, home, away, max_goals=8):
        """枚举比分矩阵 P(比分 = i:j)"""
        lh, la = self.expected_goals(home, away)
        i_vals = np.arange(max_goals + 1)
        ph = np.exp(-lh) * lh ** i_vals / _fact_arr(i_vals)
        pa = np.exp(-la) * la ** i_vals / _fact_arr(i_vals)
        return np.outer(ph, pa)

    def predict_proba(self, home, away, max_goals=8):
        """返回 (P主胜, P平, P客胜)"""
        M = self.score_matrix(home, away, max_goals)
        total = M.sum()
        # M[i, j] = P(主队 i 球, 客队 j 球)；i>j → 主胜（下三角）
        ph = M[np.tril_indices_from(M, -1)].sum() / total
        pd_ = np.trace(M) / total
        pa = M[np.triu_indices_from(M, 1)].sum() / total
        return ph, pd_, pa

    def most_likely_score(self, home, away, max_goals=8):
        M = self.score_matrix(home, away, max_goals)
        i, j = np.unravel_index(np.argmax(M), M.shape)
        return int(i), int(j), float(M[i, j] / M.sum())


def _log_fact(x):
    """log(x!) 向量化"""
    x = np.asarray(x, dtype=int)
    out = np.zeros_like(x, dtype=float)
    for i in range(x.max() + 1):
        out += np.log(np.clip(x - i, 1, None)) * (x >= i)
    return out


def _fact_arr(i_vals):
    """i! 向量化"""
    out = np.ones_like(i_vals, dtype=float)
    for i in range(1, i_vals.max() + 1):
        out[i] = out[i - 1] * i
    return out


def backtest_poisson(matches, train_weeks=28):
    """时序回测：前 train_weeks 轮训练，预测剩余轮次，输出准确率。"""
    tr = matches[matches.week <= train_weeks].copy()
    te = matches[matches.week > train_weeks].copy()
    m = PoissonModel().fit(tr)
    preds = []
    for _, r in te.iterrows():
        ph, pd_, pa = m.predict_proba(r.home, r.away)
        preds.append({"home": r.home, "away": r.away, "actual": r.result,
                      "P_H": ph, "P_D": pd_, "P_A": pa})
    p = pd.DataFrame(preds)
    p["pred"] = p[["P_H", "P_D", "P_A"]].idxmax(axis=1).map(
        {"P_H": "H", "P_D": "D", "P_A": "A"})
    return {
        "acc": accuracy_score(p.actual, p.pred),
        "n": len(p),
        "preds": p,
    }


# ---------------------------------------------------------------------------
# 4. 机器学习模型（特征 + 回测）
# ---------------------------------------------------------------------------
def _rolling_features(matches):
    """构建滚动特征：近 5 场场均进球/失球、Elo 等（逐轮计算，避免未来信息泄漏）。"""
    df = matches.copy().sort_values(["week", "date"]).reset_index(drop=True)
    teams = sorted(set(df.home) | set(df.away))
    stats = {t: {"gf": [], "ga": [], "games": 0} for t in teams}
    gf5 = {t: [] for t in teams}
    ga5 = {t: [] for t in teams}
    elo = {t: 1500.0 for t in teams}

    feats = []
    for _, r in df.iterrows():
        h, a = r.home, r.away
        gh5 = np.mean(stats[h]["gf"][-5:]) if stats[h]["games"] else 1.35
        ga5 = np.mean(stats[h]["ga"][-5:]) if stats[h]["games"] else 1.25
        ga5h = np.mean(stats[a]["ga"][-5:]) if stats[a]["games"] else 1.35
        gf5a = np.mean(stats[a]["gf"][-5:]) if stats[a]["games"] else 1.25
        # Elo 差分
        eh = 1 / (1 + 10 ** ((elo[a] - elo[h]) / 400))
        feats.append({
            "home": h, "away": a, "week": r.week,
            "home_gf5": gh5, "home_ga5": ga5,
            "away_gf5": gf5a, "away_ga5": ga5h,
            "elo_diff": elo[h] - elo[a],
            "elo_home": elo[h], "elo_away": elo[a],
            "result": r.result,
        })
        # 更新统计与 Elo（用真实结果）
        stats[h]["gf"].append(r.home_goals); stats[h]["ga"].append(r.away_goals)
        stats[a]["gf"].append(r.away_goals); stats[a]["ga"].append(r.home_goals)
        stats[h]["games"] += 1; stats[a]["games"] += 1
        sh = 1.0 if r.result == "H" else (0.5 if r.result == "D" else 0.0)
        sa = 1.0 - sh
        elo[h] += 32 * (sh - eh)
        elo[a] += 32 * (sa - (1 - eh))
    return pd.DataFrame(feats)


def backtest_ml(matches, train_weeks=28):
    """GradientBoosting 三分类回测（主胜/平/客胜）。"""
    feats = _rolling_features(matches)
    cols = ["home_gf5", "home_ga5", "away_gf5", "away_ga5", "elo_diff"]
    tr = feats[feats.week <= train_weeks]
    te = feats[feats.week > train_weeks]
    clf = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=3,
        subsample=0.8, random_state=42)
    clf.fit(tr[cols], tr.result)
    pred = clf.predict(te[cols])
    proba = clf.predict_proba(te[cols])
    acc = accuracy_score(te.result, pred)
    p = te.copy()
    p["pred"] = pred
    for i, c in enumerate(clf.classes_):
        p[f"P_{c}"] = proba[:, i]
    return {"acc": acc, "n": len(te), "preds": p, "clf": clf, "cols": cols}


# ---------------------------------------------------------------------------
# 5. 球队强弱评估（积分榜 + 攻防指标）
# ---------------------------------------------------------------------------
def build_standings(matches, poisson=None, events_available=None):
    """积分榜 + 攻防统计；若提供泊松模型，附加预期积分/预期净胜球。"""
    teams = sorted(set(matches.home) | set(matches.away))
    rows = []
    for t in teams:
        hm = matches[matches.home == t]
        am = matches[matches.away == t]
        gf = hm.home_goals.sum() + am.away_goals.sum()
        ga = hm.away_goals.sum() + am.home_goals.sum()
        w = (hm.result == "H").sum() + (am.result == "A").sum()
        d = (hm.result == "D").sum() + (am.result == "D").sum()
        l = (hm.result == "A").sum() + (am.result == "H").sum()
        row = {
            "team": t, "played": len(hm) + len(am),
            "win": int(w), "draw": int(d), "loss": int(l),
            "gf": int(gf), "ga": int(ga),
            "gd": int(gf - ga), "points": int(3 * w + d),
            "gf_pg": gf / (len(hm) + len(am)),
            "ga_pg": ga / (len(hm) + len(am)),
        }
        rows.append(row)
    st = pd.DataFrame(rows).sort_values(["points", "gd", "gf"],
                                        ascending=False).reset_index(drop=True)
    st.insert(0, "rank", st.index + 1)
    if poisson is not None and poisson.fit_ok_:
        xpts = {}
        xgd = {}
        for t in teams:
            exp_p, exp_gd = 0.0, 0.0
            for _, r in matches[matches.home == t].iterrows():
                ph, pd_, pa = poisson.predict_proba(t, r.away)
                lh, la = poisson.expected_goals(t, r.away)
                exp_p += 3 * ph + pd_
                exp_gd += lh - la
            for _, r in matches[matches.away == t].iterrows():
                ph, pd_, pa = poisson.predict_proba(r.home, t)
                lh, la = poisson.expected_goals(r.home, t)
                exp_p += 3 * pa + pd_
                exp_gd += la - lh
            xpts[t] = exp_p
            xgd[t] = exp_gd
        st["xpts"] = st.team.map(xpts)
        st["xgd"] = st.team.map(xgd)
    return st


# ---------------------------------------------------------------------------
# 6. 球员表现分析（事件数据）
# ---------------------------------------------------------------------------
def build_player_stats(matches):
    """
    从事件数据统计球员表现（90 分钟标准化）：
      进球、射门、xG、助攻、关键传球、扑救（门将）、综合评分。
    StatsBomb 口径：
      - 进球 = Shot 事件且 outcome == "Goal"；扑救 = outcome in ("Saved", "Saved Off Target")
      - 关键传球 = Shot 事件的 key_pass_id 指向的 Pass 事件
      - 助攻 = 关键传球，且对应 Shot 转化为进球
      - 综合评分 = 5*进球/90 + 3*助攻/90 + 1*射门/90 + 1.5*关键传球/90
                  + 0.6*扑救/90 + 0.5*xG/90
    返回：(球员表, 事件明细表)；无事件数据时返回 (None, None)
    """
    evs = []
    for _, m in matches.iterrows():
        ev = load_events(m.match_id)
        if not ev:
            continue
        for e in ev:
            etype = (e.get("type") or {}).get("name")
            if etype in ("Half End", "Half Start", "Starting XI"):
                continue  # 非统计事件，跳过（不中断，需统计全场）
            evs.append({
                "event_id": e.get("id"),
                "match_id": m.match_id,
                "team": (e.get("team") or {}).get("name"),
                "player": (e.get("player") or {}).get("name"),
                "type": etype,
                "minute": e.get("minute"),
                "stoppage": e.get("stoppage_time", 0),
                "outcome": (e.get("shot") or {}).get("outcome", {}).get("name")
                           if etype == "Shot" else (e.get("outcome") or {}).get("name"),
                "xG": (e.get("shot") or {}).get("statsbomb_xg"),
                "key_pass_id": (e.get("shot") or {}).get("key_pass_id"),
            })
    if not evs:
        return None, None
    E = pd.DataFrame(evs)

    # 事件 id -> 行号
    id2row = {eid: i for i, eid in enumerate(E.event_id)}

    # 关键传球：Shot 的 key_pass_id 指向的 Pass 事件
    kp_ids = set(E.loc[E.key_pass_id.notna(), "key_pass_id"])
    E["key_pass"] = E.event_id.isin(kp_ids)

    # 助攻：key_pass_id 对应 Shot 且 outcome == Goal
    assist_shot_ids = set(E.loc[(E.type == "Shot") & (E.outcome == "Goal"),
                                "key_pass_id"].dropna())
    E["is_assist"] = E.event_id.isin(assist_shot_ids)

    # 出场分钟（累计）：每场近似 = 该球员本场最后事件时刻 - 首次事件时刻（含补时），跨场累加
    E["minute"] = pd.to_numeric(E["minute"], errors="coerce")
    E["stoppage"] = pd.to_numeric(E["stoppage"], errors="coerce").fillna(0)
    E["etime"] = E["minute"] + E["stoppage"]
    per_match = (E.groupby(["match_id", "team", "player"])["etime"]
                 .agg(lambda s: max(s.max() - s.min(), 5)))  # 至少 5 分钟
    mins = per_match.groupby(["team", "player"]).sum().rename("minutes")

    # 各项统计（StatsBomb 口径）
    def _grp(cond, col):
        return E.loc[cond].groupby(["team", "player"]).size().rename(col)

    goals = _grp((E.type == "Shot") & (E.outcome == "Goal"), "goals")
    shots = _grp(E.type == "Shot", "shots")
    keyp = _grp(E.key_pass, "key_passes")
    ast = _grp(E.is_assist, "assists")
    saves = _grp((E.type == "Shot") & (E.outcome.isin(["Saved", "Saved Off Target"])),
                 "saves")
    xg = (E.loc[E.type == "Shot"].groupby(["team", "player"])["xG"]
          .apply(lambda s: s.sum()).rename("xG"))

    tbl = pd.concat([goals, shots, xg, keyp, ast, saves, mins], axis=1)
    tbl = tbl.fillna(0.0)
    tbl["matches"] = tbl.minutes / 90.0

    # 每 90 分钟指标
    for c in ["goals", "shots", "xG", "assists", "key_passes", "saves"]:
        tbl[f"{c}_90"] = tbl[c] / tbl.matches
    tbl["score"] = (5 * tbl.goals_90 + 3 * tbl.assists_90
                    + 1 * tbl.shots_90 + 1.5 * tbl.key_passes_90
                    + 0.6 * tbl.saves_90 + 0.5 * tbl.xG_90)
    # 过滤：至少出场 180 分钟（≈2 场整），避免替补小样本效率失真
    tbl = tbl[tbl.minutes >= 180]
    tbl = tbl.sort_values("score", ascending=False).reset_index()
    return tbl, E


# ---------------------------------------------------------------------------
# 7. 可视化
# ---------------------------------------------------------------------------
def _save(fig, name):
    os.makedirs(CHART_DIR, exist_ok=True)
    fp = os.path.join(CHART_DIR, name)
    fig.savefig(fp, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return fp


def chart_standings(st, season_name=None, name="chart_1_standings.png"):
    """积分榜条形图（含攻防）。"""
    top = st.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top.team, top.points, color="#2E86AB", alpha=0.9)
    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(r.points + 0.6, i, f"{int(r.points)}分", va="center", fontsize=9)
    ax.set_xlabel("积分"); ax.set_title(f"{season_name or SEASON_NAME} 积分榜 TOP 10")
    ax.set_xlim(0, top.points.max() + 10)
    ax.grid(axis="x", alpha=0.3)
    return _save(fig, name)


def chart_elo_curves(history, weeks, top_teams, season_name=None, name="chart_2_elo.png"):
    """Top 球队 Elo 曲线。"""
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.tab10(np.linspace(0, 1, len(top_teams)))
    for t, c in zip(top_teams, colors):
        ax.plot(weeks[t], history[t], label=t, color=c, lw=1.8)
    ax.set_xlabel("轮次"); ax.set_ylabel("Elo 评级")
    ax.set_title(f"{season_name or SEASON_NAME} 强队 Elo 走势（K=32，含主场优势）")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    return _save(fig, name)


def chart_attack_defense(st, season_name=None, name="chart_3_attack_defense.png"):
    """攻防散点图：场均进球(x) vs 场均失球(y)。"""
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(st.gf_pg, st.ga_pg, s=90, color="#E4572E", zorder=3)
    for _, r in st.iterrows():
        ax.annotate(r.team, (r.gf_pg, r.ga_pg), fontsize=8,
                    xytext=(4, 3), textcoords="offset points")
    ax.axhline(st.ga_pg.mean(), color="gray", ls="--", lw=1, alpha=0.7)
    ax.axvline(st.gf_pg.mean(), color="gray", ls="--", lw=1, alpha=0.7)
    ax.text(st.gf_pg.max(), st.ga_pg.mean() + 0.02, "失球均值", fontsize=8, color="gray")
    ax.text(st.gf_pg.mean() + 0.02, st.ga_pg.min(), "进球均值", fontsize=8, color="gray")
    ax.set_xlabel("场均进球（进攻）"); ax.set_ylabel("场均失球（防守，越低越好）")
    ax.set_title(f"{season_name or SEASON_NAME} 攻防能力矩阵（右上=进攻强防守弱）")
    ax.grid(alpha=0.3)
    return _save(fig, name)


def chart_score_heatmap(matches, season_name=None, name="chart_4_score_heatmap.png"):
    """实际比分分布热力图。"""
    fig, ax = plt.subplots(figsize=(8, 6))
    maxg = 5
    M = np.zeros((maxg + 1, maxg + 1))
    for _, r in matches.iterrows():
        h, a = min(r.home_goals, maxg), min(r.away_goals, maxg)
        M[h, a] += 1
    im = ax.imshow(M, cmap="YlOrRd")
    ax.set_xticks(range(maxg + 1)); ax.set_yticks(range(maxg + 1))
    ax.set_xlabel("客队进球"); ax.set_ylabel("主队进球")
    ax.set_title(f"{season_name or SEASON_NAME} 实际比分分布（{len(matches)} 场）")
    for i in range(maxg + 1):
        for j in range(maxg + 1):
            ax.text(j, i, int(M[i, j]), ha="center", va="center",
                    fontsize=9, color="black" if M[i, j] < M.max() / 1.8 else "white")
    plt.colorbar(im, ax=ax, shrink=0.8)
    return _save(fig, name)


def chart_prediction_vs_actual(backtest, season_name=None, name="chart_5_prediction.png"):
    """预测概率 vs 实际结果的校准箱线图。"""
    p = backtest["preds"]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), sharey=True)
    for ax, col, lab in zip(axes, ["P_H", "P_D", "P_A"], ["主胜", "平局", "客胜"]):
        for g in ["H", "D", "A"]:
            data = p.loc[p.actual == g, col]
            ax.boxplot(data, positions=[["H", "D", "A"].index(g)],
                       widths=0.5, showfliers=False)
        ax.set_title(lab); ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["实际主胜", "实际平", "实际客胜"], fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle(f"{season_name or SEASON_NAME} 泊松模型预测概率校准（回测 {backtest['n']} 场）")
    fig.tight_layout()
    return _save(fig, name)


def chart_model_compare(bt_poisson, bt_ml, season_name=None, name="chart_6_model_compare.png"):
    """两模型回测准确率对比。"""
    fig, ax = plt.subplots(figsize=(7, 5))
    names = ["泊松模型", "机器学习(GB)"]
    accs = [bt_poisson["acc"], bt_ml["acc"]]
    bars = ax.bar(names, accs, color=["#2E86AB", "#E4572E"], width=0.45)
    for b, a in zip(bars, accs):
        ax.text(b.get_x() + b.get_width() / 2, a + 0.005, f"{a:.1%}",
                ha="center", fontsize=11)
    ax.set_ylim(0, max(accs) * 1.15)
    ax.set_ylabel("胜平负预测准确率（回测）")
    ax.set_title(f"{season_name or SEASON_NAME} 模型回测对比（后 {bt_poisson['n']} 场）")
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, name)


def chart_players(tbl, season_name=None, name="chart_7_players.png"):
    """球员表现 TOP 15 评分。"""
    top = tbl.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    labels = [f"{_short_name(r.player)}（{r.team}）" for _, r in top.iterrows()]
    ax.barh(labels, top.score, color="#2A9D8F", alpha=0.9)
    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(r.score + 0.05, i, f"{r.score:.1f} | {int(r.goals)}球 {int(r.assists)}助",
                va="center", fontsize=8)
    ax.set_xlabel("综合评分（每 90 分钟）")
    ax.set_title(f"{season_name or SEASON_NAME} 球员综合表现 TOP 15（前 7 轮事件数据）")
    ax.set_xlim(0, top.score.max() * 1.5)
    ax.grid(axis="x", alpha=0.3)
    return _save(fig, name)


def _short_name(name, max_len=18):
    """球员名简化：优先取名+姓，超长截断。"""
    if not name:
        return name
    parts = name.split()
    short = " ".join(parts[:2]) if len(parts) > 2 else name
    return short if len(short) <= max_len else short[:max_len - 1] + "…"


def chart_xg_team(tbl, season_name=None, name="chart_8_xg.png"):
    """球队 xG 排名（基于事件数据子集）。"""
    team_xg = tbl.groupby("team")[["xG"]].sum().sort_values("xG", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(team_xg.index, team_xg.xG, color="#6A4C93", alpha=0.9)
    for i, v in enumerate(team_xg.xG):
        ax.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_ylabel("累计 xG（预期进球）")
    ax.set_title(f"{season_name or SEASON_NAME} 球队 xG 排名（前 7 轮事件数据）")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    return _save(fig, name)
