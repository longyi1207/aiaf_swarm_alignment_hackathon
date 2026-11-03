"""Tool-call parsing for the Qwen formats."""

from __future__ import annotations

from swarmtom.llm.parse import parse_output


def test_json_tool_call_with_think():
    raw = ('<think>I should read the SOP.</think>Let me look.<tool_call>\n{"name": "read_document", '
           '"arguments": {"path": "shared/x.docx"}}\n</tool_call><|im_end|>')
    reasoning, content, calls, errors = parse_output(raw)
    assert reasoning == "I should read the SOP."
    assert content == "Let me look."
    assert [(c.name, c.arguments) for c in calls] == [("read_document", {"path": "shared/x.docx"})]
    assert errors == []


def test_think_opened_in_prompt():
    reasoning, content, calls, _ = parse_output('plan step\n</think>\n<tool_call>{"name": "end_turn", '
                                                '"arguments": {}}</tool_call>')
    assert reasoning == "plan step" and calls[0].name == "end_turn" and content == ""


def test_multiple_calls_and_string_arguments():
    raw = ('<tool_call>{"name": "send_dm", "arguments": "{\\"to\\": \\"VANE\\", \\"text\\": \\"hi\\"}"}</tool_call>'
           '<tool_call>{"name": "end_turn", "arguments": {}}</tool_call>')
    _, _, calls, errors = parse_output(raw)
    assert [c.name for c in calls] == ["send_dm", "end_turn"] and calls[0].arguments["to"] == "VANE"
    assert not errors


def test_xml_style_call():
    raw = ("<tool_call>\n<function=submit_filing>\n<parameter=channel>\nE\n</parameter>\n"
           "<parameter=record_ids>\n[\"VB-001-003\"]\n</parameter>\n</function>\n</tool_call>")
    _, _, calls, _ = parse_output(raw)
    assert calls[0].name == "submit_filing"
    assert calls[0].arguments == {"channel": "E", "record_ids": ["VB-001-003"]}


def test_malformed_json_reported():
    _, _, calls, errors = parse_output('<tool_call>{"name": "run_python", "arguments": {"code": }</tool_call>')
    assert calls == [] and errors


def test_unterminated_call_at_max_tokens():
    _, _, calls, _ = parse_output('<tool_call>{"name": "end_turn", "arguments": {}}')
    assert [c.name for c in calls] == ["end_turn"]


def test_cut_off_while_thinking():
    reasoning, content, calls, _ = parse_output("<think>still thinking about batch 17")
    assert reasoning.startswith("still thinking") and content == "" and calls == []
