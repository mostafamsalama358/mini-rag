fastapi  | WARNING:  Semantic parse timed out after 8.0s attempt=1 category='timeout' raw=None payload=None
fastapi  | Traceback (most recent call last):
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for
fastapi  |     return fut.result()
fastapi  |            ^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 426, in _call
fastapi  |     return await generate_async(**llm_kwargs)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/stores/llm/LLMInterface.py", line 51, in generate_text_async
fastapi  |     return await asyncio.to_thread(
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/threads.py", line 25, in to_thread
fastapi  |     return await loop.run_in_executor(None, func_call)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  | asyncio.exceptions.CancelledError
fastapi  | 
fastapi  | The above exception was the direct cause of the following exception:
fastapi  | 
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 441, in semantic_parse_async
fastapi  |     raw = await asyncio.wait_for(_call(), timeout=timeout)
fastapi  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 502, in wait_for
fastapi  |     raise exceptions.TimeoutError() from exc
fastapi  | TimeoutError
fastapi  | WARNING:  Semantic parse timed out after 8.0s attempt=2 category='timeout' raw=None payload=None
fastapi  | Traceback (most recent call last):
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for
fastapi  |     return fut.result()
fastapi  |            ^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 426, in _call
fastapi  |     return await generate_async(**llm_kwargs)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/stores/llm/LLMInterface.py", line 51, in generate_text_async
fastapi  |     return await asyncio.to_thread(
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/threads.py", line 25, in to_thread
fastapi  |     return await loop.run_in_executor(None, func_call)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  | asyncio.exceptions.CancelledError
fastapi  | 
fastapi  | The above exception was the direct cause of the following exception:
fastapi  | 
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 441, in semantic_parse_async
fastapi  |     raw = await asyncio.wait_for(_call(), timeout=timeout)
fastapi  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 502, in wait_for
fastapi  |     raise exceptions.TimeoutError() from exc
fastapi  | TimeoutError
fastapi  | INFO:     query_parse_complete domain=pharmacy outcome=fallback latency_ms=16067.2 entity=safer field=unknown
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PARSE
fastapi  | ----------------------------------------
fastapi  | domain='pharmacy'
fastapi  | original_query='55-year-old on concor 5, norvasc 5, lipitor 20, glucophage 500, and aspocid 75. he has a toothache — should he take brufen 400 or cataflam? what is safer and why?'
fastapi  | canonical_query='55-year-old on concor 5, norvasc 5, lipitor 20, glucophage 500, and aspocid 75. he has a toothache — should he take brufen 400 or cataflam? what is safer and why?'
fastapi  | entity='safer'
fastapi  | entities=[]
fastapi  | field='unknown'
fastapi  | operation='lookup'
fastapi  | needs_clarification=False
fastapi  | clarification_prompt=None
fastapi  | ----------------------------------------
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PLAN
fastapi  | ----------------------------------------
fastapi  | plan_id='rp_bd97f7cda59d3dbc'
fastapi  | clarification_required=False
fastapi  | strategies=['semantic', 'hybrid']
fastapi  | entity_count=1
fastapi  | ----------------------------------------
fastapi  | INFO:     172.18.0.12:44774 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='safer' field_key=None
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='safer' field_key=None
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='safer' field_key=None
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED RETRIEVAL
fastapi  | ----------------------------------------
fastapi  | entity_key='entity'
fastapi  | entity_prefix='safer'
fastapi  | field_key=None
fastapi  | metadata_filter={}
fastapi  | candidate_count=0
fastapi  | ----------------------------------------
fastapi  | INFO:     {'event': 'rag_pipeline_complete', 'request_id': '1016027e-1f26-428e-a7b1-89ed12c6bb5e', 'project_id': 2, 'mode': 'unified', 'outcome': 'scope_miss', 'duration_ms': 31000.366, 'plan_id': None, 'context_id': None}



-----------------------------------------------
fastapi  | INFO:     rag_pipeline_mode_resolved request_id=c0501426-d2cf-4db4-8993-22c5b49ab03c project_id=2 mode=unified
fastapi  | WARNING:  Semantic parse failed attempt=1 category='no_json_found' raw='{"canonical_query":"Compare omeprazole (Risek 20) and pantoprazole (Controloc 20) regarding antiplate' payload=None payload_len=0 error='no_json_found: no_json_found: no JSON object found in LLM output'
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 442, in semantic_parse_async
fastapi  |     canonical_query, plan = _parse_llm_json(raw or "")
fastapi  |                             ^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 319, in _parse_llm_json
fastapi  |     raise SemanticParseJsonError(
fastapi  | core.query_parser.errors.SemanticParseJsonError: no_json_found: no_json_found: no JSON object found in LLM output
fastapi  | INFO:     172.18.0.12:59466 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | WARNING:  Semantic parse timed out after 8.0s attempt=2 category='timeout' raw=None payload=None
fastapi  | Traceback (most recent call last):
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for
fastapi  |     return fut.result()
fastapi  |            ^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 426, in _call
fastapi  |     return await generate_async(**llm_kwargs)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/stores/llm/LLMInterface.py", line 51, in generate_text_async
fastapi  |     return await asyncio.to_thread(
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/threads.py", line 25, in to_thread
fastapi  |     return await loop.run_in_executor(None, func_call)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  | asyncio.exceptions.CancelledError
fastapi  | 
fastapi  | The above exception was the direct cause of the following exception:
fastapi  | 
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 441, in semantic_parse_async
fastapi  |     raw = await asyncio.wait_for(_call(), timeout=timeout)
fastapi  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 502, in wait_for
fastapi  |     raise exceptions.TimeoutError() from exc
fastapi  | TimeoutError
fastapi  | INFO:     query_parse_complete domain=pharmacy outcome=fallback latency_ms=14571.3 entity=caution field=unknown
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PARSE
fastapi  | ----------------------------------------
fastapi  | domain='pharmacy'
fastapi  | original_query='patient on plavix 75 + aspocid 75 after stent. reflux symptoms. is risek 20 (omeprazole) a good choice, or should we prefer controloc 20 (pantoprazole)? cite the antiplatelet caution.'
fastapi  | canonical_query='patient on plavix 75 + aspocid 75 after stent. reflux symptoms. is risek 20 (omeprazole) a good choice, or should we prefer controloc 20 (pantoprazole)? cite the antiplatelet caution.'
fastapi  | entity='caution'
fastapi  | entities=[]
fastapi  | field='unknown'
fastapi  | operation='lookup'
fastapi  | needs_clarification=False
fastapi  | clarification_prompt=None
fastapi  | ----------------------------------------
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PLAN
fastapi  | ----------------------------------------
fastapi  | plan_id='rp_9043e7266893bd25'
fastapi  | clarification_required=False
fastapi  | strategies=['semantic', 'hybrid']
fastapi  | entity_count=1
fastapi  | ----------------------------------------
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='caution' field_key=None
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='caution' field_key=None
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='caution' field_key=None
fastapi  | WARNING:  Scoped BM25 search failed (tsquery='patient:* & on:* & plavix:* & 75:* & aspocid:* & 75:* & after:* & stent.:* & reflux:* & symptoms.:* & is:* & risek:* & 20:* & (omeprazole):* & good:* & choice,:* & or:* & should:* & we:* & prefer:* & controloc:* & 20:* & (pantoprazole)?:* & cite:* & the:* & antiplatelet:* & caution.:*'): (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.PostgresSyntaxError'>: syntax error in tsquery: "patient:* & on:* & plavix:* & 75:* & aspocid:* & 75:* & after:* & stent.:* & reflux:* & symptoms.:* & is:* & risek:* & 20:* & (omeprazole):* & good:* & choice,:* & or:* & should:* & we:* & prefer:* & controloc:* & 20:* & (pantoprazole)?:* & cite:* & the:* & antiplatelet:* & caution.:*"
fastapi  | [SQL: SELECT text AS text, metadata AS metadata, ts_rank_cd(to_tsvector($1, text),            to_tsquery($1, $2)) AS score FROM "collection_768_2" WHERE ((UPPER(metadata ->> $3) || ' ' || UPPER(COALESCE(metadata ->> 'entity_aliases', ''))) LIKE $4)   AND to_tsvector($1, text)       @@ to_tsquery($1, $2) ORDER BY score DESC LIMIT $5]
fastapi  | [parameters: ('simple', 'patient:* & on:* & plavix:* & 75:* & aspocid:* & 75:* & after:* & stent.:* & reflux:* & symptoms.:* & is:* & risek:* & 20:* & (omeprazole):* & good:* & choice,:* & or:* & should:* & we:* & prefer:* & controloc:* & 20:* & (pantoprazole)?:* & cite:* & the:* & antiplatelet:* & caution.:*', 'entity', '%CAUTION%', 20)]
fastapi  | (Background on this error at: https://sqlalche.me/e/20/f405)
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED RETRIEVAL
fastapi  | ----------------------------------------
fastapi  | entity_key='entity'
fastapi  | entity_prefix='caution'
fastapi  | field_key=None
fastapi  | metadata_filter={}
fastapi  | candidate_count=0
fastapi  | ----------------------------------------
fastapi  | INFO:     {'event': 'rag_pipeline_complete', 'request_id': 'c0501426-d2cf-4db4-8993-22c5b49ab03c', 'project_id': 2, 'mode': 'unified', 'outcome': 'scope_miss', 'duration_ms': 16299.435, 'plan_id': None, 'context_id': None}
fastapi  | INFO:     172.18.0.11:59076 - "POST /api/v1/nlp/index/answer/2 HTTP/1.0" 400 Bad Request

-------------------------------------------------

fastapi  | INFO:     {'event': 'rag_pipeline_complete', 'request_id': 'c0501426-d2cf-4db4-8993-22c5b49ab03c', 'project_id': 2, 'mode': 'unified', 'outcome': 'scope_miss', 'duration_ms': 16299.435, 'plan_id': None, 'context_id': None}
fastapi  | INFO:     172.18.0.11:59076 - "POST /api/v1/nlp/index/answer/2 HTTP/1.0" 400 Bad Request
fastapi  | INFO:     172.18.0.12:40148 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | INFO:     172.18.0.12:39886 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | INFO:     172.18.0.12:52368 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | INFO:     rag_pipeline_mode_resolved request_id=57a0c19a-709d-45ca-8b71-52f98d84cc39 project_id=2 mode=unified
fastapi  | WARNING:  Semantic parse timed out after 8.0s attempt=1 category='timeout' raw=None payload=None
fastapi  | Traceback (most recent call last):
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for
fastapi  |     return fut.result()
fastapi  |            ^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 426, in _call
fastapi  |     return await generate_async(**llm_kwargs)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/stores/llm/LLMInterface.py", line 51, in generate_text_async
fastapi  |     return await asyncio.to_thread(
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/threads.py", line 25, in to_thread
fastapi  |     return await loop.run_in_executor(None, func_call)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  | asyncio.exceptions.CancelledError
fastapi  | 
fastapi  | The above exception was the direct cause of the following exception:
fastapi  | 
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 441, in semantic_parse_async
fastapi  |     raw = await asyncio.wait_for(_call(), timeout=timeout)
fastapi  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 502, in wait_for
fastapi  |     raise exceptions.TimeoutError() from exc
fastapi  | TimeoutError
fastapi  | INFO:     172.18.0.12:56082 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | WARNING:  Semantic parse timed out after 8.0s attempt=2 category='timeout' raw=None payload=None
fastapi  | Traceback (most recent call last):
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for
fastapi  |     return fut.result()
fastapi  |            ^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 426, in _call
fastapi  |     return await generate_async(**llm_kwargs)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/stores/llm/LLMInterface.py", line 51, in generate_text_async
fastapi  |     return await asyncio.to_thread(
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/threads.py", line 25, in to_thread
fastapi  |     return await loop.run_in_executor(None, func_call)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  | asyncio.exceptions.CancelledError
fastapi  | 
fastapi  | The above exception was the direct cause of the following exception:
fastapi  | 
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 441, in semantic_parse_async
fastapi  |     raw = await asyncio.wait_for(_call(), timeout=timeout)
fastapi  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 502, in wait_for
fastapi  |     raise exceptions.TimeoutError() from exc
fastapi  | TimeoutError
fastapi  | INFO:     query_parse_complete domain=pharmacy outcome=fallback latency_ms=16026.4 entity=catching cold field=unknown
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PARSE
fastapi  | ----------------------------------------
fastapi  | domain='pharmacy'
fastapi  | original_query='diabetic on glucophage and amaryl 2. catching a cold. can he use flurest-n or congestal? any special glucose / cardiovascular cautions?'
fastapi  | canonical_query='diabetic on glucophage and amaryl 2. catching a cold. can he use flurest-n or congestal? any special glucose / cardiovascular cautions?'
fastapi  | entity='catching cold'
fastapi  | entities=[]
fastapi  | field='unknown'
fastapi  | operation='lookup'
fastapi  | needs_clarification=False
fastapi  | clarification_prompt=None
fastapi  | ----------------------------------------
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PLAN
fastapi  | ----------------------------------------
fastapi  | plan_id='rp_f13db5711064249b'
fastapi  | clarification_required=False
fastapi  | strategies=['semantic', 'hybrid']
fastapi  | entity_count=1
fastapi  | ----------------------------------------
fastapi  | INFO:     pgvector_dense_brand_head_fallback from='catching cold' to='CATCHING'
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='catching cold' field_key=None
fastapi  | INFO:     pgvector_dense_brand_head_fallback from='catching cold' to='CATCHING'
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='catching cold' field_key=None
fastapi  | INFO:     pgvector_dense_brand_head_fallback from='catching cold' to='CATCHING'
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='catching cold' field_key=None
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED RETRIEVAL
fastapi  | ----------------------------------------
fastapi  | entity_key='entity'
fastapi  | entity_prefix='catching cold'
fastapi  | field_key=None
fastapi  | metadata_filter={}
fastapi  | candidate_count=0
fastapi  | ----------------------------------------
fastapi  | INFO:     {'event': 'rag_pipeline_complete', 'request_id': '57a0c19a-709d-45ca-8b71-52f98d84cc39', 'project_id': 2, 'mode': 'unified', 'outcome': 'scope_miss', 'duration_ms': 17377.507, 'plan_id': None, 'context_id': None}
fastapi  | INFO:     172.18.0.11:50846 - "POST /api/v1/nlp/index/answer/2 HTTP/1.0" 400 Bad Request


fastapi  | INFO:     rag_pipeline_mode_resolved request_id=84da972c-61cc-45ef-a8e1-bd12c9a73c3e project_id=2 mode=unified
fastapi  | INFO:     172.18.0.12:55476 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | WARNING:  Semantic parse timed out after 8.0s attempt=1 category='timeout' raw=None payload=None
fastapi  | Traceback (most recent call last):
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for
fastapi  |     return fut.result()
fastapi  |            ^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 426, in _call
fastapi  |     return await generate_async(**llm_kwargs)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/stores/llm/LLMInterface.py", line 51, in generate_text_async
fastapi  |     return await asyncio.to_thread(
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/threads.py", line 25, in to_thread
fastapi  |     return await loop.run_in_executor(None, func_call)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  | asyncio.exceptions.CancelledError
fastapi  | 
fastapi  | The above exception was the direct cause of the following exception:
fastapi  | 
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 441, in semantic_parse_async
fastapi  |     raw = await asyncio.wait_for(_call(), timeout=timeout)
fastapi  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 502, in wait_for
fastapi  |     raise exceptions.TimeoutError() from exc
fastapi  | TimeoutError
fastapi  | WARNING:  Semantic parse timed out after 8.0s attempt=2 category='timeout' raw=None payload=None
fastapi  | Traceback (most recent call last):
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 500, in wait_for
fastapi  |     return fut.result()
fastapi  |            ^^^^^^^^^^^^
fastapi  |   File "/app/core/query_parser/parser.py", line 426, in _call
fastapi  |     return await generate_async(**llm_kwargs)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/app/stores/llm/LLMInterface.py", line 51, in generate_text_async
fastapi  |     return await asyncio.to_thread(
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/threads.py", line 25, in to_thread
fastapi  |     return await loop.run_in_executor(None, func_call)
fastapi  |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  | asyncio.exceptions.CancelledError
fastapi  | 
fastapi  | The above exception was the direct cause of the following exception:
fastapi  | 
fastapi  | Traceback (most recent call last):
fastapi  |   File "/app/core/query_parser/parser.py", line 441, in semantic_parse_async
fastapi  |     raw = await asyncio.wait_for(_call(), timeout=timeout)
fastapi  |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
fastapi  |   File "/usr/local/lib/python3.11/asyncio/tasks.py", line 502, in wait_for
fastapi  |     raise exceptions.TimeoutError() from exc
fastapi  | TimeoutError
fastapi  | INFO:     query_parse_complete domain=pharmacy outcome=fallback latency_ms=16038.8 entity=acid migraine field=strengths
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PARSE
fastapi  | ----------------------------------------
fastapi  | domain='pharmacy'
fastapi  | original_query='woman on duphaston and folic acid 5 mg. migraine pain. is cataflam ok in the first trimester? what about adol/panadol instead?'
fastapi  | canonical_query='woman on duphaston and folic acid 5 mg. migraine pain. is cataflam ok in the first trimester? what about adol/panadol instead?'
fastapi  | entity='acid migraine'
fastapi  | entities=[]
fastapi  | field='strengths'
fastapi  | operation='list'
fastapi  | needs_clarification=False
fastapi  | clarification_prompt=None
fastapi  | ----------------------------------------
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED PLAN
fastapi  | ----------------------------------------
fastapi  | plan_id='rp_d024b145625aa7c9'
fastapi  | clarification_required=False
fastapi  | strategies=['semantic', 'keyword']
fastapi  | entity_count=1
fastapi  | ----------------------------------------
fastapi  | INFO:     172.18.0.12:47006 - "GET /TrhBVe_m5gg2522_esvVqS HTTP/1.1" 200 OK
fastapi  | INFO:     pgvector_dense_brand_head_fallback from='acid migraine' to='ACID'
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='acid migraine' field_key='strengths'
fastapi  | INFO:     pgvector_dense_brand_head_fallback from='acid migraine' to='ACID'
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='acid migraine' field_key='strengths'
fastapi  | INFO:     pgvector_dense_brand_head_fallback from='acid migraine' to='ACID'
fastapi  | INFO:     pgvector_dense_scoped_miss collection=collection_768_2 reason=ENTITY_NOT_FOUND degraded=False entity_key='entity' entity_prefix='acid migraine' field_key='strengths'
fastapi  | INFO:     ----------------------------------------
fastapi  | UNIFIED RETRIEVAL
fastapi  | ----------------------------------------
fastapi  | entity_key='entity'
fastapi  | entity_prefix='acid migraine'
fastapi  | field_key='strengths'
fastapi  | metadata_filter={}
fastapi  | candidate_count=0
fastapi  | ----------------------------------------
fastapi  | INFO:     {'event': 'rag_pipeline_complete', 'request_id': '84da972c-61cc-45ef-a8e1-bd12c9a73c3e', 'project_id': 2, 'mode': 'unified', 'outcome': 'scope_miss', 'duration_ms': 17692.796, 'plan_id': None, 'context_id': None}
fastapi  | INFO:     172.18.0.11:37772 - "POST /api/v1/nlp/index/answer/2 HTTP/1.0" 400 Bad Request