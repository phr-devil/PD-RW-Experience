# Independent review and source-byte evidence — v0.1.1

## Authority boundary

- A case's `source_refs.sha256` value is a **claim**, not a hash the software previously checked.
- A lesson's `status=REVIEWED` and `review_ref` are **declared metadata**. Without separate signed review receipt and real source bytes, they confer no retrieval authority.
- Receipt and key are **separate** from untrusted Case and Lesson files. In production, an authenticated host must provision a pinned trusted Ed25519 public key and source-index; an Agent must not be free to replace that trust configuration.
- A verified signature means the trusted key holder signed that exact JSON subject. It does not prove novelty, causal truth, permission for model training, or a PD-RW rule change.

## Canonical receipt shape

Signed bytes are UTF-8 JSON produced with `json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)` and the subject fingerprint is SHA-256 of the corresponding canonical JSON representation.

~~~json
{
  "payload": {
    "schema_version": "1.0",
    "kind": "LESSON_REVIEW",
    "subject_sha256": "<64 lowercase hex characters>",
    "reviewed_at": "2026-11-21",
    "decision": "APPROVED_FOR_ADVISORY"
  },
  "signature": "<base64 Ed25519 detached signature>"
}
~~~

Supported kinds:
- `LESSON_REVIEW`: subject = entire Lesson JSON record.
- `TARGET_REVIEW`: subject = `{"case_id": id, "case_sha256": digest(case), "reviewed_target": target}`.
- `ACE_RUN_GRANT`: subject = the precise model/provider/ACE revision/data digests/call and time budget in `ace_bridge.py`.

Sign each `payload` with the authorized review/grant private key **outside this repository and outside untrusted Agent processes**. No private signer is shipped here. Approving a source/lesson and authorizing a paid model run are conceptually distinct operations; production hosts may require separate signing roles even where the MVP accepts one trusted public key.

## Source index

Supply a JSON object mapping each Case ID to an object of source ID → *relative* path below the host-controlled `--source-root`:

~~~json
{"CASE-A": {"doi:example": "papers/approved-paper.pdf"}}
~~~

All referenced source bytes are streamed and hashed; missing files, changed bytes and paths resolved outside the root block. No symlink escape, unrestricted filesystem scan or private artifact upload is attempted. Original access permissions still come from the host.

## Availability semantics

`case.available_at` and `source.available_at` describe the earliest date the case/source could legitimately be used. `reviewed_target.reviewed_at` and signed receipt `reviewed_at` must be at or before the task's `--as-of` cutoff. A later receipt cannot retroactively authorize a historical lesson. Signed review cannot prove an unsigned claim of original publication time was true; independent metadata validation remains advisable.

## What remains NOT verified

- Accuracy of paper claims and experiment effects.
- Scientific equivalence or defensibility of the generalization.
- Current author permissions or host process isolation.
- Truthful identity of a caller supplying its own key; host must pin trust keys.
- Provider-side billing cap (enforce separately).

Do not promote Experience results to PD-RW rules automatically.
