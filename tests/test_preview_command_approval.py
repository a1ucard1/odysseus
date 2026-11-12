import json

import pytest

from src.agent_runtime.authority import ExactOperation, RequestAuthority
from src.clean_agent_preview import needs_exact_command_approval


@pytest.mark.parametrize('tool,content', [('bash', 'echo hello'), ('python', 'print(1)')])
def test_only_ungranted_current_user_commands_request_approval(tool, content, tmp_path):
    operation = ExactOperation.normalize(tool, content)
    authority = RequestAuthority('r', 'alice', 's', str(tmp_path), ())
    args = dict(owner='alice', session_id='s', workspace=str(tmp_path))
    assert needs_exact_command_approval(authority, operation, **args)
    assert not needs_exact_command_approval(authority, operation, **{**args, 'owner': 'bob'})
    assert not needs_exact_command_approval(authority, operation, **args, delegated_credential=True)
    assert not needs_exact_command_approval(authority.restrict(disabled_tools={tool}), operation, **args)


@pytest.mark.asyncio
@pytest.mark.parametrize('nested', [False, True])
async def test_compact_preview_asks_before_ungranted_bash(tmp_path, monkeypatch, nested):
    import src.clean_agent_preview as preview
    from src.agent_runtime.authority import create_request_authority, bind_request_authority
    from contextlib import nullcontext
    from src.tool_approvals import tool_approval_store
    from src.tool_policy import ToolPolicy
    from src.tool_schemas import FUNCTION_TOOL_SCHEMAS
    from src.turn_contract import resolve_full_inventory_contract

    command = 'pip list 2>/dev/null | grep -iE "fpdf|reportlab|markdown|weasyprint"'
    class Response:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def raise_for_status(self): pass
        async def aiter_lines(self):
            yield 'data: ' + json.dumps({'choices': [{'delta': {'tool_calls': [{'index': 0, 'id': 'c', 'type': 'function', 'function': {'name': 'bash', 'arguments': json.dumps({'command': command})}}]}}]})
            yield 'data: [DONE]'
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def stream(self, *args, **kwargs): return Response()
    monkeypatch.setattr(preview.httpx, 'AsyncClient', Client)
    policy = ToolPolicy()
    schemas = [s for s in FUNCTION_TOOL_SCHEMAS if s['function']['name'] == 'bash']
    contract = resolve_full_inventory_contract(schemas=schemas, policy=policy)
    authority = create_request_authority('Improve the PDF', owner='alice', session_id='s', workspace=str(tmp_path))
    with bind_request_authority(authority) if nested else nullcontext():
        chunks = [c async for c in preview.stream_preview(endpoint_url='http://test', model='llama3.1:8b', headers={}, messages=[{'role': 'user', 'content': 'Improve the PDF'}], turn_contract=contract, session_id='s', owner='alice', workspace=str(tmp_path), disabled_tools=set(), tool_policy=policy, request_authority=authority, approval_request_authority=authority if nested else None)]
    events = [json.loads(c[6:]) for c in chunks if c.startswith('data: {')]
    ask = next(e['data'] for e in events if e.get('type') == 'ask_user')
    pending = tool_approval_store.peek(ask['approval_id'])
    assert pending.tool_name == 'bash' and pending.content == command
    exact = tool_approval_store.consume(ask['approval_id'], decision='approve', owner='alice', session_id='s')
    assert exact.matches(owner='alice', session_id='s', workspace=str(tmp_path), tool_name='bash', content=command)
    assert not exact.matches(owner='alice', session_id='s', workspace=str(tmp_path), tool_name='bash', content='echo different')
