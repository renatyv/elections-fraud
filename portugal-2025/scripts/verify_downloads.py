#!/usr/bin/env python3
"""Проверка выгрузок портала MAI: суммы голосов по нижнему уровню (фрегезии/
консульства) против национального итога, полнота файлов результатов.

Использование: python3 scripts/verify_downloads.py [каталоги data/*_mai ...]
Без аргументов проверяет все data/*_mai, где есть territory-tree.json.
"""
import glob
import json
import os
import sys


def load_result(res_dir, key):
    key = str(key)
    for f in glob.glob(os.path.join(res_dir, key + "-*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d.get("data"), dict):
            d = d["data"]
        cur = d.get("currentResults")
        if cur:
            return cur
    return None


def main():
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    dirs = sys.argv[1:] or sorted(glob.glob(os.path.join(base, "*_mai")))
    ok_all = True
    for d in dirs:
        tree_p = os.path.join(d, "territory-tree.json")
        if not os.path.exists(tree_p):
            continue
        tree = json.load(open(tree_p, encoding="utf-8"))
        tree = {str(k): v for k, v in tree.items()}
        res_dirs = glob.glob(os.path.join(d, "territory-results*"))
        name = os.path.basename(d)
        if not res_dirs:
            print(f"{name}: нет territory-results — пропущено")
            continue
        for res_dir in res_dirs:
            files = glob.glob(os.path.join(res_dir, "*.json"))
            # национальный итог: корень дерева (parent=None) с максимумом голосов;
            # в старом формате это GLOBAL-990000, в новом — «Universo Global» с числовым id
            roots = [k for k, v in tree.items() if v.get("parent") is None]
            national = None
            for cand in roots:
                r = load_result(res_dir, cand)
                if r and (national is None or (r.get("totalVoters") or 0) > national[1].get("totalVoters", 0)):
                    national = (cand, r)
            # суммы по листьям; корни (level 0) не считаем — иначе агрегат
            # попадёт в сумму дважды (в старом портале GLOBAL-990000 — «лист»
            # с пустым списком детей)
            leaf_votes = 0
            leaf_voters = 0
            n_missing = 0
            for k, v in tree.items():
                if v.get("children") is not None or v.get("level", 99) == 0:
                    continue
                r = load_result(res_dir, k)
                if r is None:
                    n_missing += 1
                    continue
                leaf_votes += r.get("totalVoters") or 0
                leaf_voters += r.get("subscribedVoters") or 0
            tag = os.path.basename(res_dir)
            if national is None:
                print(f"{name} [{tag}]: {len(files)} файлов, {n_missing} листьев без результата, "
                      f"национальный итог не найден — проверьте выгрузку")
                ok_all = False
                continue
            nat_key, nat = national
            dv = nat.get("totalVoters") or 0
            ds = nat.get("subscribedVoters") or 0
            # национальный итог GLOBAL включает заграницу; листья покрывают всё дерево
            cover_v = leaf_votes / dv * 100 if dv else 0
            cover_s = leaf_voters / ds * 100 if ds else 0
            top = ", ".join(
                f"{p['acronym']} {p.get('percentage', 0)}%"
                for p in sorted(nat.get("resultsParty") or [],
                                key=lambda x: -(x.get("votes") or 0))[:3])
            status = "OK" if n_missing == 0 and abs(cover_v - 100) < 0.5 else "ПРОВЕРИТЬ"
            if status != "OK":
                ok_all = False
            print(f"{name} [{tag}]: {status} — листьев без результата: {n_missing}; "
                  f"сумма голосов листьев {cover_v:.2f}% от {nat_key}; "
                  f"избирателей {cover_s:.2f}%; явка {nat.get('percentageVoters')}%; топ: {top}")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
