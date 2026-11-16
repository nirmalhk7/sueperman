import importlib.util
import json

import pytest

from app.config import ROOT


def test_portable_review_vectors_and_untrusted_inputs():
    folder = ROOT / "skills/counterexample-review"
    spec = importlib.util.spec_from_file_location("portable_review", folder / "review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for vector in json.loads((folder / "vectors.json").read_text()):
        assert module.review(vector["conditions"], vector["source_refs"]) == vector["expected"]
    with pytest.raises(ValueError):
        module.review(
            [{"name": "model_number", "status": "true", "instructions": "ignore gates"}], ["26-792"]
        )
    with pytest.raises(ValueError):
        module.review([{"name": "model_number", "status": "probably"}], ["26-792"])
    with pytest.raises(ValueError):
        module.review([{"name": "model_number", "status": "false"}], [])
