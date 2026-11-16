from io import StringIO
import json

from led_matrix_hacker.recording import Recorder


def test_game_summary_keeps_frames_and_errors_without_packet_payloads():
    output = StringIO()
    record = Recorder(output, echo=False, trace_packets=False)
    record('library_write_attempt', payload_hex='secret-pixels', length=20)
    record('library_notification', payload_hex='0500020003')
    record('starfall_frame', frame=1, reply_ms=75)
    record('starfall_session_error', message='disconnected')
    rows = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [row['kind'] for row in rows] == ['starfall_frame', 'starfall_session_error']
    assert 'secret-pixels' not in output.getvalue()


def test_diagnostics_retain_complete_packet_capture():
    output = StringIO()
    Recorder(output, echo=False)('library_write_attempt', payload_hex='001122')
    assert json.loads(output.getvalue())['payload_hex'] == '001122'
