"""Convert a hyper-tau recording and its kept kit into the build-trajectory visualizer's files.

usage: python3 recording-to-trajectory.py <recording.json> <result.json> <kit/workspace> \\
           <out dir> <slot> "<builder label>" [--no-manifest]

Writes rel<slot>.json (the trajectory), rel<slot>.kit.json (the submitted workspace) and
rel<slot>.row.json (the build's row for the manifest) into <out dir>. With <out dir> the
site's public/build-trajectories/ the row also goes into manifest.json there, so the site
lists the build; --no-manifest leaves every manifest alone (a run that lands its files on a
served site through server.mjs's PUT sends the three files itself).

A recording keeps no tool-result ids, so a result is paired with the oldest open call.
"""
import json
import pathlib
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
flags = {a for a in sys.argv[1:] if a.startswith("--")}
if len(args) != 6:
    sys.exit(__doc__)
rec_path, result_path, kit_ws, out_dir, slot, label = args
rec = json.load(open(rec_path))
res = json.load(open(result_path))

items = []
pending = []  # the recording keeps no result ids: a result answers the oldest open call
for e in rec["events"]:
    t = e["type"]
    if t == "sandbox_phase":
        items.append({"k": "phase", "phase": e["phase"], "detail": e.get("detail", "")})
    elif t == "client_message":
        items.append({"k": "client", "text": e["content"]})
    elif t == "sandbox_step":
        s = e["step"]
        if e.get("thinking"):
            items.append({"k": "text", "s": s, "text": e["thinking"]})
        for tc in e.get("tool_calls") or []:
            pending.append(tc.get("name", ""))
            items.append({"k": "call", "s": s, "tool": tc.get("name", ""), "args": tc.get("arguments") or {}})
        for tr in e.get("tool_results") or []:
            text = str(tr.get("result", ""))
            items.append({"k": "result", "s": s, "tool": (pending.pop(0) if pending else tr.get("name", "")), "text": text[:2000], "full": len(text) > 2000})
    elif t == "sandbox_done":
        items.append({"k": "done", "reason": e["reason"], "steps": e["steps"], "tool_calls": e["tool_calls"]})
    elif t == "final_eval_start":
        items.append({"k": "final_eval"})


def task_description() -> str:
    """The task's brief: the recording's copy, else the task file in this repository."""
    meta = rec.get("task_metadata", {}) or {}
    text = meta.get("task_description") or meta.get("description")
    if text:
        return text
    task_file = pathlib.Path(__file__).resolve().parents[3] / "data/tau2/hyper/tasks" / f"{res['task_id']}.json"
    if task_file.exists():
        return json.load(open(task_file)).get("task_description", "")
    return ""


details = res["test_details"]
build = res.get("build_result") or {}
traj = {
    "v": 1, "slot": slot, "task_id": res["task_id"], "domain": res["source_domain"], "description": task_description(),
    "builder": {"harness": res["developer_harness"], "model": res["developer_llm"]}, "builder_label": label,
    "stats": {"steps": res.get("total_outer_steps", build.get("total_steps", 0)), "tool_calls": build.get("total_tool_calls", 0)},
    "result": {"initial": 0, "final": res["final_test_reward"], "eval_passed": sum(1 for d in details if d["reward"] == 1.0), "eval_total": len(details)},
    "eval_tasks": [[str(d["task_id"]), d["reward"]] for d in details], "items": items,
}
files, skipped = [], []
ws = pathlib.Path(kit_ws)
for p in (sorted(ws.rglob("*")) if ws.exists() else []):
    if p.is_file():
        rel = str(p.relative_to(ws))
        try:
            files.append({"path": rel, "size": p.stat().st_size, "text": p.read_text()})
        except UnicodeDecodeError:
            skipped.append(rel)
kit = {"v": 1, "slot": slot, "task_id": res["task_id"], "builder": traj["builder"], "builder_label": label, "files": files, "skipped": skipped}
row = {
    "slot": slot, "file": f"rel{slot}.json", "task_id": res["task_id"], "domain": res["source_domain"],
    "builder": traj["builder"], "builder_label": label, "steps": traj["stats"]["steps"], "tool_calls": traj["stats"]["tool_calls"],
    "final": traj["result"]["final"], "eval_passed": traj["result"]["eval_passed"], "eval_total": traj["result"]["eval_total"],
}
out = pathlib.Path(out_dir)
out.mkdir(parents=True, exist_ok=True)
(out / f"rel{slot}.json").write_text(json.dumps(traj))
(out / f"rel{slot}.kit.json").write_text(json.dumps(kit))
(out / f"rel{slot}.row.json").write_text(json.dumps(row, indent=1))
if "--no-manifest" not in flags and (out / "manifest.json").exists():
    m = json.load(open(out / "manifest.json"))
    m["tasks"] = [t for t in m["tasks"] if t["slot"] != slot] + [row]
    (out / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
print("items", len(items), "files", len(files), "->", out / f"rel{slot}.json")
