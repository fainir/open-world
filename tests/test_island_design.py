"""Place-only previews against local SQLite and a simulated included text provider."""
import asyncio
import json
import math
import os
import secrets
import threading
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import test_security  # Isolate DATA_DIR and VERSIONS_DIR before importing the app.
from app.backend import included_ai
from app.backend.database import SessionLocal, init_db
from app.backend.island_design import _cache_lock, _deltas
from app.backend.main import app
from app.backend.models import ChatMessage, ChatSession, GameVersion, IncludedCreation, User
from app.backend.request_limits import _buckets


def part(identifier, **changes):
    return dict(dict(id=identifier, kind='box', x=0, y=0, z=0, rotation=0,
                     scale=[4, 2, 4], color='#aabbee'), **changes)


def proposal(*parts):
    return {'title': 'Beach pavilion', 'summary': 'A new pavilion above the water.',
            'scene': {'version': 1, 'objects': list(parts)}}


def answer(body=None, reason='end_turn'):
    return SimpleNamespace(stop_reason=reason, content=[SimpleNamespace(
        type='text', text=body if isinstance(body, str) else json.dumps(body or proposal(part('roof', y=4))))])


class IslandDesign(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        init_db()
        self.db = SessionLocal()
        self.db.query(IncludedCreation).delete()
        self.db.commit()
        _buckets.clear()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://open-world.gg')
        self.headers = {'X-OpenWorld-Guest': secrets.token_urlsafe(32), 'Idempotency-Key': str(uuid.uuid4())}
        self.payload = {'title': 'Pier', 'prompt': 'Add a blue roof to my pavilion',
                        'scene': {'version': 1, 'objects': [part('pier')]}}
        self.ready = patch.object(included_ai, 'ready', return_value=True)
        self.ready.start()
        self.addCleanup(self.ready.stop)

    async def asyncTearDown(self):
        await self.client.aclose()
        self.db.close()

    async def post(self, payload=None, headers=None):
        return await self.client.post('/api/island/place-design', json=self.payload if payload is None else payload,
                                      headers=self.headers if headers is None else headers)

    async def remaining(self):
        return (await self.client.get('/api/creation-allowance', headers=self.headers)).json()['remaining']

    async def test_extends_source_and_replays_without_creating_or_editing_original_game(self):
        models = [User, ChatSession, ChatMessage, GameVersion]
        before = [self.db.query(model).count() for model in models]
        initial_files = sorted(os.listdir(os.environ['VERSIONS_DIR']))
        with (patch.object(included_ai, 'generate', return_value=answer(proposal(
                part('pier', scale=[199, 100, 9]), part('roof', y=4)))) as provider,
              patch('app.backend.main.run_agent') as game_editor,
              patch('app.backend.agent.anthropic.Anthropic') as direct):
            first = await self.post()
            self.assertEqual(first.status_code, 200, first.text)
            body = first.json()
            self.assertEqual(set(body), {'title', 'scene', 'summary'})
            self.assertEqual(body['scene']['objects'], [part('pier'), part('roof', y=4)])
            self.assertIn('no-store', first.headers['cache-control'])
            self.assertEqual((await self.post()).json(), body)
            self.assertEqual(await self.remaining(), 1)
            provider.assert_called_once()
            game_editor.assert_not_called()
            direct.assert_not_called()
            system, messages = provider.call_args.args
            self.assertIn('one private place', system)
            self.assertEqual(json.loads(messages[0]['content']), self.payload)
            self.assertEqual(provider.call_args.kwargs['request_id'], self.headers['Idempotency-Key'])
            self.assertNotIn(self.headers['X-OpenWorld-Guest'], str(provider.call_args))
        record = self.db.get(IncludedCreation, self.headers['Idempotency-Key'])
        self.assertEqual((record.status, record.session_id, record.version_id), ('complete', None, None))
        self.assertEqual([self.db.query(model).count() for model in models], before)
        self.assertEqual(sorted(os.listdir(os.environ['VERSIONS_DIR'])), initial_files)

    async def test_place_uses_existing_signed_text_profile_without_tools_or_game_source(self):
        result = {'ok': True, 'request_id': self.headers['Idempotency-Key'], 'model': included_ai.MODEL,
                  'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': json.dumps(proposal(part('new-roof')))}]}
        with patch.object(included_ai, 'build_opener') as stub:
            response = stub.return_value.open.return_value.__enter__.return_value
            response.status = 200
            response.read.return_value = json.dumps(result).encode()
            actual = await self.post()
        self.assertEqual(actual.status_code, 200, actual.text)
        opening = stub.return_value.open.call_args.args[0]
        envelope = json.loads(opening.data)
        self.assertEqual(opening.full_url, included_ai.GATEWAY)
        self.assertIsNotNone(opening.get_header('X-portfolio-signature'))
        self.assertEqual((envelope['app'], envelope['feature']), ('openworld', 'generate'))
        self.assertEqual(set(envelope['input']), {'system', 'messages'})
        self.assertEqual(json.loads(envelope['input']['messages'][0]['content']), self.payload)
        self.assertEqual(len(envelope['actor']), 64)
        self.assertEqual(len(envelope['actor_ip']), 64)

    async def test_oversized_body_and_untrusted_origin_cannot_start_preview(self):
        with patch.object(included_ai, 'generate') as provider:
            large = await self.client.post('/api/island/place-design', headers=self.headers,
                                           content=b'x' * (192 * 1024 + 1))
            self.assertEqual(large.status_code, 413)
            forbidden = await self.post(headers={**self.headers, 'Origin': 'https://example.invalid'})
            self.assertEqual(forbidden.status_code, 403)
            provider.assert_not_called()

    async def test_revisions_only_touch_returned_private_parts(self):
        self.payload.update(prompt='Repaint the pier blue')
        self.payload['scene']['objects'].append(part('bench', x=8))
        with patch.object(included_ai, 'generate', return_value=answer(proposal(part('pier', color='#1759ff')))):
            resp = await self.post()
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()['scene']['objects'], [part('pier', color='#1759ff'), part('bench', x=8)])

    async def test_wire_rejects_extra_fields_code_and_out_of_bounds_before_provider(self):
        bad = [
            {**self.payload, 'html': '<html></html>'},
            {**self.payload, 'prompt': '<script>alert(1)</script>'},
            {**self.payload, 'title': 'x' * 81},
            {**self.payload, 'scene': {'version': True, 'objects': []}},
            {**self.payload, 'scene': {'version': 1, 'objects': [part('a', x='3')]}},
            {**self.payload, 'scene': {'version': 1, 'objects': [part('a', x=True)]}},
            {**self.payload, 'scene': {'version': 1, 'objects': [part('a', scale=[18, 2, 18], x=245, rotation=math.pi/4)]}},
            {**self.payload, 'scene': {'version': 1, 'objects': [part('a'), part('a')]}},
            {**self.payload, 'scene': {'version': 1, 'objects': [part('a', url='https://example.invalid/asset')]}},
        ]
        with patch.object(included_ai, 'generate') as provider:
            for payload in bad:
                with self.subTest(payload=payload):
                    response = await self.post(payload)
                    self.assertEqual(response.status_code, 422, response.text)
            provider.assert_not_called()
        self.assertEqual(self.db.query(IncludedCreation).count(), 0)

    async def test_output_rejects_code_external_fields_bad_geometry_and_truncation(self):
        invalid = [answer('<html><script>1</script></html>'), answer({**proposal(part('x')), 'map': {}}),
                   answer(proposal(part('x', color='https://example.invalid/'))),
                   answer(proposal(part('x', y=253, scale=[4, 4, 4]))),
                   answer(proposal(part('x', x=260))), answer(reason='max_tokens')]
        for outgoing in invalid:
            with self.subTest(outgoing=outgoing):
                self.db.query(IncludedCreation).delete()
                self.db.commit()
                _buckets.clear()
                self.headers['Idempotency-Key'] = str(uuid.uuid4())
                with patch.object(included_ai, 'generate', return_value=outgoing) as provider:
                    response = await self.post()
                    self.assertEqual(response.status_code, 502, response.text)
                    self.assertEqual(response.json()['code'], 'invalid_result')
                    self.assertNotIn('scene', response.json())
                    self.assertEqual((await self.post()).status_code, 409)
                    self.assertEqual(await self.remaining(), 1)
                    provider.assert_called_once()

    async def test_merged_object_count_cannot_bypass_limit(self):
        self.payload['scene']['objects'] = [part(f'p{i}') for i in range(256)]
        with patch.object(included_ai, 'generate', return_value=answer()):
            self.assertEqual((await self.post()).status_code, 502)

    async def test_shared_actor_limit_and_failure_refunds(self):
        with patch.object(included_ai, 'generate', side_effect=included_ai.IncludedError(
                'budget_paused', 'Synthetic', dispatched=False)) as provider:
            self.assertEqual((await self.post()).status_code, 503)
            self.assertEqual(await self.remaining(), 2)
            self.assertEqual((await self.post()).status_code, 409)
            provider.assert_called_once()
        with patch.object(included_ai, 'generate', return_value=answer()) as provider:
            for count in (1, 0):
                self.headers['Idempotency-Key'] = str(uuid.uuid4())
                self.assertEqual((await self.post()).status_code, 200)
                self.assertEqual(await self.remaining(), count)
            self.headers['Idempotency-Key'] = str(uuid.uuid4())
            self.assertEqual((await self.post()).status_code, 429)
            self.assertEqual(provider.call_count, 2)
        original = {'message': 'Synthetic', 'request_id': str(uuid.uuid4()), 'funding': 'included'}
        with patch('app.backend.main.run_agent') as editor:
            response = await self.client.post('/api/chat', json=original, headers=self.headers)
            self.assertEqual(response.status_code, 429)
            editor.assert_not_called()

    async def test_idempotency_binds_scene_and_guest_and_cannot_charge_after_cache_loss(self):
        with patch.object(included_ai, 'generate', return_value=answer()) as provider:
            self.assertEqual((await self.post()).status_code, 200)
            self.assertEqual((await self.post({**self.payload, 'title': 'Other'})).status_code, 409)
            self.assertEqual((await self.post(headers={**self.headers, 'X-OpenWorld-Guest': secrets.token_urlsafe(32)})).status_code, 409)
            with patch.object(included_ai, 'ready', return_value=False):
                self.assertEqual((await self.post()).status_code, 200)
            with _cache_lock:
                _deltas.pop(self.headers['Idempotency-Key'])
            self.assertEqual((await self.post()).json()['code'], 'preview_unavailable')
            provider.assert_called_once()

    async def test_fail_closed_for_missing_proof_invalid_reference_and_unavailable_allowance(self):
        with patch.object(included_ai, 'generate') as provider:
            self.assertEqual((await self.post(headers={'Idempotency-Key': str(uuid.uuid4())})).status_code, 400)
            self.assertEqual((await self.post(headers={**self.headers, 'Idempotency-Key': 'invalid'})).status_code, 400)
            with patch.object(included_ai, 'ready', return_value=False):
                self.assertEqual((await self.post()).status_code, 503)
            with patch.dict(os.environ, {'RAILWAY_ENVIRONMENT_ID': 'standin'}):
                self.assertEqual((await self.post()).status_code, 503)
            provider.assert_not_called()
        self.assertEqual(self.db.query(IncludedCreation).count(), 0)

    async def test_unknown_dispatch_and_concurrent_retries_never_dispatch_twice(self):
        started, release = threading.Event(), threading.Event()
        def uncertain(*args, **kwargs):
            started.set()
            release.wait(4)
            raise included_ai.IncludedError('outcome_unknown', 'Synthetic')
        with patch.object(included_ai, 'generate', side_effect=uncertain) as provider:
            original = asyncio.create_task(self.post())
            self.assertTrue(await asyncio.to_thread(started.wait, 3))
            try:
                self.assertEqual((await self.post()).json()['code'], 'in_progress')
            finally:
                release.set()
            self.assertEqual((await original).status_code, 503)
            self.assertEqual((await self.post()).status_code, 409)
            self.assertEqual(await self.remaining(), 1)
            provider.assert_called_once()
