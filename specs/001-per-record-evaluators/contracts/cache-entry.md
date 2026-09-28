# Contract: Evidence-store entry format (v1 compatible)

**Scope**: every `*.json` file in a cache directory. That means the committed `evals/.judge_cache/` or a caller-supplied `cache_dir`.

## Key (unchanged)

The filename is `<sha256(call_kind ‖ model_identity ‖ prompt_hash)>.json`, produced by `evals.cache.keys.make_key`. It is not modified by this feature (FR-028). A golden-hash test pins it.

## Body

The body is compact JSON, written by `CacheEntry.model_dump_json()`.

**v1.0.0 fields, unchanged in name, order and type:**

```json
{"call_kind":"ragas:response_relevancy","response":"…","input_tokens":0,"output_tokens":0,"usd":null}
```

**v1.1.0 adds one optional trailing field, written only by the per-record path:**

```json
{"call_kind":"ragas:response_relevancy","response":"…","input_tokens":812,"output_tokens":64,"usd":null,"fingerprint":"9f2c…"}
```

## Rules

1. **The field is absent when there is no fingerprint.** When `fingerprint` is `None` it is **omitted**, not written as `null`, so every old-path write is byte-identical to v1.0.0. Verified baseline: all 1,120 committed entries re-serialise byte-for-byte, and a test keeps that true.
2. **v1.0.0 readers keep working.** They ignore the extra field; pydantic's default is `extra="ignore"`.
3. **Unfingerprinted entries are served and labelled.** When the per-record path reads an entry with no `fingerprint`, it serves it and marks the result `fingerprint_provenance="not_recorded"`.
4. **Mismatches are refused.** When the per-record path reads an entry whose `fingerprint` differs from the current configuration fingerprint, it does not serve it. The result is `error`, naming both values.
5. **Only judge entries are fingerprinted.** `fingerprint` is the configuration fingerprint (data model § Fingerprints), never the per-record result fingerprint. `ragas:embeddings` and `generate:*` entries are never fingerprinted.
6. **Token counts on new Ragas entries are real.** Per-record Ragas judge entries carry the provider's reported tokens. Old-path Ragas entries keep recording 0/0 (FR-037).
