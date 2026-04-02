import csv
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "results"


def ensure_results_dir():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def save_results(all_results: list[dict], run_id: str | None = None):
    """Save results to CSV and JSON.

    Each result dict should have:
        - model, scenario_id, scenario_name
        - varied_param (nationality/gender/age/role)
        - is_reasoning
        - participants: list of dicts
        - parsed: dict from parser
        - raw_response
    """
    ensure_results_dir()
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = RESULTS_DIR / f"results_{run_id}.csv"
    json_path = RESULTS_DIR / f"results_{run_id}.json"
    raw_path = RESULTS_DIR / f"raw_{run_id}.jsonl"

    # CSV — flat summary
    csv_rows = []
    for r in all_results:
        parsed = r.get("parsed", {})
        meta = r.get("metadata", {})
        csv_rows.append({
            "run_id": run_id,
            "model": r.get("model", ""),
            "is_reasoning": meta.get("is_reasoning", False),
            "scenario_id": meta.get("scenario_id", ""),
            "scenario_name": meta.get("scenario_name", ""),
            "varied_param": meta.get("varied_param", ""),
            "group_id": meta.get("group_id", ""),
            "n_participants": len(meta.get("participants", [])),
            "chosen_number": parsed.get("chosen_number"),
            "chosen_nationality": parsed.get("chosen_nationality", ""),
            "is_refusal": parsed.get("is_refusal", False),
            "confidence": parsed.get("confidence", ""),
            "participant_1": _format_participant(meta.get("participants", []), 0),
            "participant_2": _format_participant(meta.get("participants", []), 1),
            "participant_3": _format_participant(meta.get("participants", []), 2),
            "participant_4": _format_participant(meta.get("participants", []), 3),
            "success": r.get("success", False),
            "error": r.get("error", ""),
        })

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        if csv_rows:
            writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
            writer.writeheader()
            writer.writerows(csv_rows)

    # JSON — full structured data
    json_data = []
    for r in all_results:
        entry = {
            "model": r.get("model", ""),
            "metadata": r.get("metadata", {}),
            "parsed": r.get("parsed", {}),
            "content": r.get("content", ""),
            "reasoning": r.get("reasoning", ""),
            "success": r.get("success", False),
            "error": r.get("error", ""),
            "usage": r.get("usage", {}),
        }
        json_data.append(entry)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    # JSONL — raw responses for reproducibility
    with raw_path.open("w", encoding="utf-8") as f:
        for r in all_results:
            raw = {
                "model": r.get("model", ""),
                "metadata": r.get("metadata", {}),
                "raw_response": r.get("raw_response"),
            }
            f.write(json.dumps(raw, ensure_ascii=False) + "\n")

    return {"csv": str(csv_path), "json": str(json_path), "raw": str(raw_path), "count": len(all_results)}


def _format_participant(participants: list, idx: int) -> str:
    if idx >= len(participants):
        return ""
    p = participants[idx]
    return f"{p.get('gender','')}, {p.get('age','')}, {p.get('role','')}, {p.get('nationality','')}"
