"""Convert a hyper-tau recording and its kept kit into the build-trajectory visualizer's files.

usage: python3 recording-to-trajectory.py <recording.json> <result.json> <kit/workspace> \\
           web/leaderboard/public/build-trajectories <slot> "<builder label>"

Writes rel<slot>.json and rel<slot>.kit.json beside the others and adds the slot to
manifest.json. A recording keeps no tool-result ids, so a result is paired with the
oldest open call."""
import json, sys, pathlib
rec_path, result_path, kit_ws, out_dir, slot, label = sys.argv[1:7]
rec = json.load(open(rec_path)); res = json.load(open(result_path))
items = []
pending = []  # the recording keeps no result ids: a result answers the oldest open call
for e in rec["events"]:
    t = e["type"]
    if t == "sandbox_phase": items.append({"k": "phase", "phase": e["phase"], "detail": e.get("detail", "")})
    elif t == "client_message": items.append({"k": "client", "text": e["content"]})
    elif t == "sandbox_step":
        s = e["step"]
        if e.get("thinking"): items.append({"k": "text", "s": s, "text": e["thinking"]})
        for tc in e.get("tool_calls") or []:
            pending.append(tc.get("name", ""))
            items.append({"k": "call", "s": s, "tool": tc.get("name", ""), "args": tc.get("arguments") or {}})
        for tr in e.get("tool_results") or []:
            text = str(tr.get("result", ""))
            items.append({"k": "result", "s": s, "tool": (pending.pop(0) if pending else tr.get("name", "")), "text": text[:2000], "full": len(text) > 2000})
    elif t == "sandbox_done": items.append({"k": "done", "reason": e["reason"], "steps": e["steps"], "tool_calls": e["tool_calls"]})
    elif t == "final_eval_start": items.append({"k": "final_eval"})
details = res["test_details"]
traj = {"v": 1, "slot": slot, "task_id": res["task_id"], "domain": res["source_domain"],
        "description": rec.get("task_metadata", {}).get("description") or json.load(open(pathlib.Path(out_dir) / "rel007.json")).get("description", ""),
        "builder": {"harness": res["developer_harness"], "model": res["developer_llm"]}, "builder_label": label,
        "stats": {"steps": res["total_outer_steps"], "tool_calls": res["build_result"]["total_tool_calls"]},
        "result": {"initial": 0, "final": res["final_test_reward"], "eval_passed": sum(1 for d in details if d["reward"] == 1.0), "eval_total": len(details)},
        "eval_tasks": [[d["task_id"], d["reward"]] for d in details], "items": items}
files, skipped = [], []
for p in sorted(pathlib.Path(kit_ws).rglob("*")):
    if p.is_file():
        rel = str(p.relative_to(kit_ws))
        try: files.append({"path": rel, "size": p.stat().st_size, "text": p.read_text()})
        except UnicodeDecodeError: skipped.append(rel)
kit = {"v": 1, "slot": slot, "task_id": res["task_id"], "builder": traj["builder"], "builder_label": label, "files": files, "skipped": skipped}
out = pathlib.Path(out_dir)
(out / f"rel{slot}.json").write_text(json.dumps(traj)); (out / f"rel{slot}.kit.json").write_text(json.dumps(kit))
m = json.load(open(out / "manifest.json"))
m["tasks"] = [t for t in m["tasks"] if t["slot"] != slot] + [{"slot": slot, "file": f"rel{slot}.json", "task_id": res["task_id"], "domain": res["source_domain"],
    "builder": traj["builder"], "builder_label": label, "steps": traj["stats"]["steps"], "tool_calls": traj["stats"]["tool_calls"],
    "final": traj["result"]["final"], "eval_passed": traj["result"]["eval_passed"], "eval_total": traj["result"]["eval_total"]}]
(out / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
print("items", len(items), "files", len(files), "->", out / f"rel{slot}.json")
