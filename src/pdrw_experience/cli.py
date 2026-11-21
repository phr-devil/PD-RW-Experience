"""Small offline-first CLI. Never reads other projects by default."""
from __future__ import annotations
import argparse
import json
import sys

from .ace_bridge import prepare_ace_samples, run_ace_offline
from .core import (RecordError, load_records, retrieve_guidance,
                   review_lesson, validate_case, validate_feedback)


def parser():
    p = argparse.ArgumentParser(prog="pdrw-exp")
    sub = p.add_subparsers(dest="command", required=True)
    check = sub.add_parser("case-check")
    check.add_argument("path")
    review = sub.add_parser("lesson-review")
    review.add_argument("path")
    review.add_argument("--cases", required=True)
    prep = sub.add_parser("ace-preflight")
    prep.add_argument("path")
    run = sub.add_parser("ace-run")
    run.add_argument("path")
    run.add_argument("--ace-root", required=True)
    run.add_argument("--provider", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--save-dir", required=True)
    run.add_argument("--execute", action="store_true")
    retrieve = sub.add_parser("retrieve")
    retrieve.add_argument("path")
    retrieve.add_argument("--cases", required=True)
    retrieve.add_argument("--task-type", required=True)
    retrieve.add_argument("--query", default="")
    retrieve.add_argument("--as-of", required=True)
    retrieve.add_argument("--limit", type=int, default=5)
    feedback = sub.add_parser("feedback-check")
    feedback.add_argument("path")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "case-check":
            cases = [validate_case(c) for c in load_records(args.path)]
            output = {"status": "SHAPE_OK_ONLY", "case_count": len(cases),
                      "scientific_validity_verified": False}
        elif args.command == "lesson-review":
            cases = load_records(args.cases)
            output = [review_lesson(x, cases) for x in load_records(args.path)]
        elif args.command == "ace-preflight":
            ready = prepare_ace_samples(load_records(args.path))
            output = {"status": ready["status"], "train_count": len(ready["train"]),
                      "val_count": len(ready["val"]), "blocked": ready["blocked"],
                      "model_calls": 0}
        elif args.command == "ace-run":
            output = run_ace_offline(
                load_records(args.path), ace_root=args.ace_root,
                provider=args.provider, model=args.model,
                save_dir=args.save_dir, execute=args.execute)
        elif args.command == "retrieve":
            output = retrieve_guidance(
                load_records(args.path), load_records(args.cases),
                task_type=args.task_type, query=args.query,
                as_of=args.as_of, limit=args.limit)
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
