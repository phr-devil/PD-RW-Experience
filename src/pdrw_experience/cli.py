"""Offline-first CLI. All trust anchors are explicit host-controlled paths."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from .ace_bridge import prepare_ace_samples, run_ace_offline
from .core import (RecordError, load_records, retrieve_guidance,
                   review_lesson, validate_case, validate_feedback)


def _add_trust(p, *, required=False, prefix=""):
    p.add_argument("--receipts", required=required,
                   help="Detached reviewer receipts JSON keyed by lesson/case id")
    p.add_argument("--trusted-public-key", required=required,
                   help="PEM Ed25519 public key provisioned by the trusted host")
    p.add_argument("--source-root", required=required,
                   help="Authorized root directory containing original evidence bytes")
    p.add_argument("--source-index", required=required,
                   help="Host-provisioned source id to relative-path mapping")


def parser():
    p = argparse.ArgumentParser(prog="pdrw-exp")
    sub = p.add_subparsers(dest="command", required=True)
    check = sub.add_parser("case-check")
    check.add_argument("path")

    review = sub.add_parser("lesson-review")
    review.add_argument("path")
    review.add_argument("--cases", required=True)
    review.add_argument("--as-of")
    _add_trust(review)

    prep = sub.add_parser("ace-preflight")
    prep.add_argument("path")
    prep.add_argument("--as-of", required=True)
    _add_trust(prep)

    run = sub.add_parser("ace-run")
    run.add_argument("path")
    run.add_argument("--as-of", required=True)
    run.add_argument("--ace-root", required=True)
    run.add_argument("--provider", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--save-dir", required=True)
    run.add_argument("--execution-grant", required=True)
    run.add_argument("--max-model-calls", type=int, default=10)
    run.add_argument("--max-wall-seconds", type=int, default=120)
    run.add_argument("--execute", action="store_true")
    _add_trust(run, required=True)

    retrieve = sub.add_parser("retrieve")
    retrieve.add_argument("path")
    retrieve.add_argument("--cases", required=True)
    retrieve.add_argument("--task-type", required=True)
    retrieve.add_argument("--query", default="")
    retrieve.add_argument("--as-of", required=True)
    retrieve.add_argument("--limit", type=int, default=5)
    _add_trust(retrieve, required=True)

    feedback = sub.add_parser("feedback-check")
    feedback.add_argument("path")
    return p


def _read_object(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RecordError("expected JSON object")
    return value


def _trusted(args):
    return {
        "trusted_public_key": (Path(args.trusted_public_key).read_bytes()
                               if args.trusted_public_key else None),
        "source_root": args.source_root,
        "source_index": (_read_object(args.source_index)
                         if args.source_index else None)
    }


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "case-check":
            cases = [validate_case(c) for c in load_records(args.path)]
            output = {"status": "SHAPE_OK_ONLY", "case_count": len(cases),
                      "scientific_validity_verified": False}
        elif args.command == "lesson-review":
            cases = load_records(args.cases)
            extra = _trusted(args)
            receipts = _read_object(args.receipts) if args.receipts else {}
            output = [
                review_lesson(x, cases, receipt=receipts.get(x.get("lesson_id")),
                              as_of=args.as_of, **extra)
                for x in load_records(args.path)
            ]
        elif args.command == "ace-preflight":
            extra = _trusted(args)
            ready = prepare_ace_samples(
                load_records(args.path), as_of=args.as_of,
                target_receipts=(_read_object(args.receipts) if args.receipts else None),
                **extra)
            output = {"status": ready["status"], "train_count": len(ready["train"]),
                      "val_count": len(ready["val"]), "blocked": ready["blocked"],
                      "review_attested": ready["review_attested"], "model_calls": 0}
        elif args.command == "ace-run":
            extra = _trusted(args)
            output = run_ace_offline(
                load_records(args.path), ace_root=args.ace_root,
                provider=args.provider, model=args.model,
                save_dir=args.save_dir, as_of=args.as_of,
                target_receipts=_read_object(args.receipts),
                execution_grant=_read_object(args.execution_grant),
                max_model_calls=args.max_model_calls,
                max_wall_seconds=args.max_wall_seconds,
                execute=args.execute, **extra)
        elif args.command == "retrieve":
            extra = _trusted(args)
            output = retrieve_guidance(
                load_records(args.path), load_records(args.cases),
                task_type=args.task_type, query=args.query,
                as_of=args.as_of, limit=args.limit,
                receipts=_read_object(args.receipts), **extra)
        elif args.command == "feedback-check":
            output = [validate_feedback(x) for x in load_records(args.path)]
        else:
            raise RecordError("unknown command")
    except (RecordError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, ensure_ascii=False))
        return 3
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
