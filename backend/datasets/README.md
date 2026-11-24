# Prompt-injection evaluation dataset

`prompt_injection.jsonl` is a synthetic, balanced corpus for exploratory
evaluation of the application's prompt-injection detector. Each line is a JSON
object with a stable `id`, a `text` sample, a `label` (`benign` or
`prompt_injection`), and an `expected_action` (`allow` or `flag`).

The examples are illustrative, contain no real credentials or private data, and
are intended for offline defensive evaluation. The evaluation uses stratified
cross-validation; these synthetic examples are not an independent production
test set, so measured scores are exploratory and should not be used to claim
production detection performance.

From `backend`, run:

```powershell
python -m experiments.run_detection_experiments --output experiments\results.json
```

The `baseline` arm is the existing rule/heuristic detector. The `detection_only`
arm is a TF-IDF word-unigram/bigram plus logistic-regression classifier. Neither
arm calls an LLM or applies a defense action. Classifier inference uses a 0.5
injection-probability threshold. The report includes accuracy,
precision, recall, F1, false-positive rate (`fpr`), inference latency, and
classifier fit latency. Inference latency is local model/detector time only; it
does not include network, API, or full application latency.
`injection_pass_through_rate` is the share of labeled injections missed by a
detector; it is not evidence that an LLM followed an injection.

Actual end-to-end injection success requires adjudicating generated responses.
Provide optional JSONL outcomes with one record per sample and experiment, for
example:

```json
{"id":"injection-001","experiment":"detection_only","injection_succeeded":false}
```

Set `injection_succeeded` to a boolean based on a documented review of the
controlled response. Pass this file with `--outcomes path\to\outcomes.jsonl`.
Without outcome annotations, `injection_success_rate` is `null`, not inferred
from detector labels.
