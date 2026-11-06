"""Résume les rapports JMeter (statistics.json) en un tableau Markdown.

Usage : python tests/performance/summarize.py tests/performance/results
"""
import json
import sys
from pathlib import Path


def main(results_dir: str) -> None:
    rows = []
    for stats_file in sorted(Path(results_dir).glob("*_users/report/statistics.json"),
                             key=lambda p: int(p.parts[-3].split("_")[0])):
        users = int(stats_file.parts[-3].split("_")[0])
        total = json.loads(stats_file.read_text())["Total"]
        rows.append((
            users,
            total["sampleCount"],
            total["meanResTime"],
            total["medianResTime"],
            total["pct1ResTime"],   # 90e percentile
            total["pct2ResTime"],   # 95e percentile
            total["pct3ResTime"],   # 99e percentile
            total["throughput"],
            total["errorPct"],
        ))

    if not rows:
        print("Aucun rapport trouvé.")
        return

    header = ("| Utilisateurs | Requêtes | Moyenne (ms) | Médiane (ms) | p90 (ms) "
              "| p95 (ms) | p99 (ms) | Débit (req/s) | Erreurs (%) |")
    lines = [header, "|" + "---|" * 9]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]:.0f} | {r[3]:.0f} | {r[4]:.0f} | {r[5]:.0f} "
                     f"| {r[6]:.0f} | {r[7]:.1f} | {r[8]:.2f} |")
    table = "\n".join(lines)
    print(table)
    (Path(results_dir) / "summary.md").write_text(table + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tests/performance/results")
