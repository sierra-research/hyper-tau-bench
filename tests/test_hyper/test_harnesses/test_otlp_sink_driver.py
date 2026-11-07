"""The OTLP sink that runs beside a harness in the construction container."""

import gzip
import json
import subprocess
import sys
import urllib.request

from tau2.hyper.harnesses import otlp_sink_driver
from tau2.hyper.harnesses.otlp_sink_driver import start_sink


def _post(endpoint: str, body: bytes, **headers: str) -> dict:
    request = urllib.request.Request(f"{endpoint}/v1/traces", data=body, method="POST", headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def test_sink_appends_each_export_request_as_one_line(tmp_path):
    out = tmp_path / "otlp" / "spans.ndjson"
    sink = start_sink(out, port=0)
    try:
        export = {"resourceSpans": [{"scopeSpans": [{"spans": [{"name": "LLM Generation", "spanId": "a1"}]}]}]}
        assert _post(sink.endpoint, json.dumps(export).encode()) == {}
        assert _post(sink.endpoint, gzip.compress(json.dumps(export).encode()), **{"content-encoding": "gzip"}) == {}
        assert _post(sink.endpoint, b"\x0a\x03abc", **{"content-type": "application/x-protobuf"}) == {}
        assert sink.received == 3
    finally:
        sink.shutdown()
        sink.server_close()
    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert [line["path"] for line in lines] == ["/v1/traces"] * 3
    # a JSON body is kept parsed, in the shape Strata's sink writes and its reader takes
    assert lines[0]["body"] == export and lines[1]["body"] == export
    assert "raw" in lines[2] and "body" not in lines[2]
    assert all("authorization" not in json.dumps(line) for line in lines)


def test_driver_runs_the_command_with_the_prompt_and_the_endpoint_set(tmp_path):
    out = tmp_path / "spans.ndjson"
    script = (
        "import json, os, sys, urllib.request; "
        "e = os.environ['OTEL_EXPORTER_OTLP_ENDPOINT']; "
        "r = urllib.request.Request(e + '/v1/traces', data=json.dumps({'resourceSpans': []}).encode(), method='POST', headers={'content-type': 'application/json'}); "
        "urllib.request.urlopen(r, timeout=5).read(); "
        "print('prompt:' + sys.argv[-1]); "
        "raise SystemExit(5)"
    )
    completed = subprocess.run(
        [sys.executable, "-m", "tau2.hyper.harnesses.otlp_sink_driver", "--out", str(out), "--port", "0", "--", sys.executable, "-c", script],
        input="Build the agent.\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 5, completed.stderr
    assert "prompt:Build the agent." in completed.stdout
    assert len(out.read_text().splitlines()) == 1


def test_driver_refuses_no_command_and_an_empty_prompt(tmp_path, monkeypatch):
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("x"))
    assert otlp_sink_driver.main(["--out", str(tmp_path / "s.ndjson")]) == 2
    monkeypatch.setattr(sys, "stdin", io.StringIO("   "))
    assert otlp_sink_driver.main(["--out", str(tmp_path / "s.ndjson"), "--", "true"]) == 2
