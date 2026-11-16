import json

import pytest

from led_matrix_hacker.cli import build_parser, main


@pytest.mark.parametrize("arguments", [
    ["scan", "--timeout", "0"],
    ["scan", "--timeout", "-1"],
    ["scan", "--timeout", "nan"],
    ["scan", "--timeout", "inf"],
    ["inspect", "MOCK-A", "--connect-timeout", "0"],
    ["listen", "MOCK-A"],
    ["listen", "MOCK-A", "--characteristic", "nope"],
    ["listen", "MOCK-A", "--characteristic", "0"],
    ["listen", "MOCK-A", "--characteristic", "0x10000"],
    ["listen", "MOCK-A", "--characteristic", "7", "--max-events", "0"],
])
def test_invalid_arguments_fail_before_bluetooth(ble, arguments):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
    assert not ble.scan_calls


def test_scan_json_file_and_stdout_are_parseable(ble, tmp_path, capsys):
    path = tmp_path / "scan.json"
    assert main(["scan", "--json", "--output", str(path)]) == 0
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report == json.loads(capsys.readouterr().out)
    assert report["devices"][0]["identifier"] == "MOCK-A"


def test_output_file_is_never_overwritten_and_fails_before_scan(ble, tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("preserve me", encoding="utf-8")
    assert main(["scan", "--output", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == "preserve me"
    assert not ble.scan_calls


def test_missing_output_parent_fails_before_scan(ble, tmp_path):
    assert main(["scan", "--output", str(tmp_path / "missing" / "scan.json")]) == 1
    assert not ble.scan_calls


def test_readable_inspection_labels_characteristics(ble, capsys):
    assert main(["inspect", "MOCK-A"]) == 0
    output = capsys.readouterr().out
    assert "writable=True  notifiable=True" in output
    assert "write-without-response" in output
    assert "handle 7" in output


def test_listen_output_is_jsonl_and_survives_event_limit(ble, tmp_path, capsys):
    ble.messages = [b"\x01", b"\x02"]
    path = tmp_path / "events.jsonl"
    assert main(["listen", "MOCK-A", "--characteristic", "0x7", "--max-events", "1", "--output", str(path)]) == 0
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    output = capsys.readouterr()
    assert events == [json.loads(line) for line in output.out.splitlines()]
    assert len(events) == 1
    assert "CCCD" in output.err


def test_empty_scan_is_success_with_actionable_message(ble, capsys):
    ble.advertisements = {}
    assert main(["scan"]) == 0
    assert "Bluetooth Classic" in capsys.readouterr().out


def test_missing_device_is_a_useful_cli_error(ble, capsys):
    assert main(["inspect", "missing"]) == 1
    assert "Device not found" in capsys.readouterr().err


def test_full_uuid_and_decimal_handle_selectors():
    parser = build_parser()
    assert parser.parse_args(["listen", "MOCK-A", "--characteristic", "7"]).characteristic == 7
    uuid = "00001234-0000-1000-8000-00805f9b34fb"
    assert parser.parse_args(["listen", "MOCK-A", "--characteristic", uuid]).characteristic == uuid
