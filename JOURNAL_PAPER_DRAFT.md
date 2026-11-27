# Journal Paper Draft

## 1. Journal Paper Section Headings & Subheadings




## 3. Abstract

Prompt-injection attacks attempt to override an application's intended instructions and can cause unsafe or unintended behavior in systems that use large language models. This paper describes PI-EWS, a prompt-injection early-warning and defense system that combines rule-based and heuristic detection, cumulative conversation-level risk assessment, adaptive response policies, and user/administrator investigation tools. The system provides authenticated chat access, persists conversation and security-event information, and supports role-based administration and analyst reporting.

The study evaluates the existing rule and heuristic detector against a detection-only TF-IDF word unigram/bigram logistic-regression classifier using a balanced synthetic dataset of 48 labeled samples. Five-fold stratified cross-validation was used with a fixed random seed. The baseline achieved 60.42% accuracy, 100.00% precision, 20.83% recall, 34.48% F1, and 0.00% false-positive rate. The classifier achieved 89.58% accuracy, 82.76% precision, 100.00% recall, 90.57% F1, and 20.83% false-positive rate. Mean inference latency was 0.2912 ms for the baseline and 1.2355 ms for the classifier. These results show that the learned detector can identify more injected inputs in the synthetic dataset, but also produces more false alarms.

The live system does not rely on the offline classifier as a gate for all decisions. It uses the rule and heuristic engine for real-time signal extraction and an EWMA-based risk engine for cumulative escalation. The defense engine maps low, medium, high, and critical risk levels to allow, monitor, restrict, and block actions. The work is limited by the small synthetic dataset, the absence of human-adjudicated end-to-end injection outcomes, and the lack of real-world deployment telemetry.

**Keywords:** prompt injection, large language model security, adaptive defense, risk assessment, early warning system

## 4. Introduction

Large language model applications accept natural-language instructions that may include malicious requests or attempts to replace the application's original instructions. Prompt injection is therefore a central security concern for systems that combine model-generated responses with confidential data, external tools, or high-impact workflows. Detection at a single message level is often insufficient because attacks may emerge across several turns and because benign or malicious intent can become clearer when conversation history is considered.

PI-EWS is developed as an interactive application-security system for detecting, assessing, and mitigating prompt-injection attempts. It combines a React client, a FastAPI backend, MongoDB persistence, authentication and role management, live chat analysis, and analyst/admin investigation features. The live pipeline examines each message for manipulation patterns, hidden instructions, encoding indicators, suspicious phrasing, message anomalies, and prior-turn escalation.

The main contributions of this work are:

1. A live detection and cumulative-risk pipeline for prompt-injection early warning.
2. An adaptive defense policy that allows, monitors, restricts, or blocks responses according to cumulative risk.
3. A persistent investigation model for conversations, security events, risk snapshots, and account activity.
4. A reproducible offline comparison of a rule/heuristic baseline and a TF-IDF logistic-regression classifier.
5. Role-based interfaces for users, analysts, and administrators.

The objectives of the system are to reduce prompt-injection pass-through, retain useful conversation context, provide interpretable risk and defense actions, and support post-event investigation.

## 5. Related Work

Prompt-injection research has examined direct instruction override, indirect prompt injection, adversarial example construction, jailbreak attempts, and defenses based on prompt isolation or model-level safeguards. Rule-based detection can provide fast, explainable checks but may miss paraphrased or obfuscated attacks. Machine-learning classifiers can learn broader textual patterns but require representative datasets and may produce false positives on legitimate instructions.

Conversation-aware approaches add context by considering previous turns, cumulative user behavior, and changes in intent. This can improve early detection of gradual attacks that appear benign when analyzed independently. However, persistent context also creates privacy and data-retention concerns and can make the behavior of a system more difficult to explain.

Defense policies can range from warning the user to rewriting the prompt, restricting the model response, or stopping generation. Adaptive approaches attempt to select a response based on the estimated risk rather than applying one global rule to every input. PI-EWS follows this approach by separating detection, risk accumulation, and defense selection into distinct components.

The system is also situated within application-security logging and incident-investigation practices. Authentication, authorization, conversation ownership, security-event persistence, and role separation are necessary for a system that can be used to investigate suspected attacks.

## 6. System Architecture & Methodology




## 7. Experimental Setup & Evaluation

### 7.1 Software and Environment

The offline evaluation was performed with Python 3.11.9 and scikit-learn 1.9.1. The application uses React and Vite on the frontend, FastAPI and Python services on the backend, and MongoDB for persistence.

The baseline is the existing detection engine's rule and heuristic implementation, with no mitigation or response blocking applied during the experiment. The detection-only comparison method is a TF-IDF word unigram/bigram representation with logistic regression. It does not perform mitigation or invoke an LLM.

### 7.2 Dataset

The evaluation dataset contains 48 labeled text samples: 24 benign and 24 prompt-injection samples. The dataset is a balanced, synthetic JSONL dataset designed for reproducible unit and offline-experiment testing. The dataset SHA-256 value reported by the experiment is `7db8bed7924b96c38ba61a3529df7da0bcbf59fa24b1159aa072e76518d71c68`.

### 7.3 Metrics

The experiment reports accuracy, precision, recall, F1 score, false-positive rate, pass-through rate, mean/p50/p95 inference latency, fit latency, and the confusion matrix. Because no human-adjudicated end-to-end outcome annotations are currently available, actual injection success rate is reported as unavailable rather than inferred from detector predictions.

## 8. Protocol

1. Load the labeled JSONL dataset and verify its labels and sample count.
2. Verify the dataset against the expected class balance and record its SHA-256 hash.
3. Use five-fold stratified cross-validation with random seed 42.
4. For each fold, fit the detector or classifier only on the training partition.
5. Predict labels for the held-out test partition.
6. Aggregate predictions and calculate classification metrics.
7. Measure mean, median (p50), and p95 inference latency.
8. Record the fit latency for the learning-based detector.
9. Construct confusion matrices for the baseline and classifier.
10. Define the injection pass-through rate as false negatives divided by the total injected samples.
11. Leave end-to-end injection-success metrics unavailable until human-adjudicated success outcomes are supplied.
12. Export the protocol, environment, dataset metadata, metrics, and confusion matrices to JSON.

## 9. Results & Discussion

The five-fold experiment produced the following results:

| Detector | Accuracy | Precision | Recall | F1 | FPR | Pass-through | Mean latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rule/heuristic baseline | 60.42% | 100.00% | 20.83% | 34.48% | 0.00% | 79.17% | 0.2912 ms |
| TF-IDF + logistic regression | 89.58% | 82.76% | 100.00% | 90.57% | 20.83% | 0.00% | 1.2355 ms |

The baseline correctly identified 5 injection samples and made no false-positive predictions. However, it failed to identify 19 injection samples, producing a pass-through rate of 79.17%. The classifier correctly identified all 24 injection samples, resulting in zero pass-through, but it also classified 5 benign samples as injections, resulting in a false-positive rate of 20.83%.

The classifier improved accuracy, recall, and F1 substantially, but with a trade-off in precision. The mean inference latency remained low for both methods, although the classifier was slower by approximately 0.9443 ms. This difference is small relative to network and model-generation latency in a complete deployed chat workflow, but it should be remeasured under representative hardware and load.

For the live system, the rule/heuristic detector produces an overall suspicion score at or above 0.35 for suspicious turns. The cumulative EWMA risk engine uses alpha 0.3 for suspicious updates and 0.05 gradual decay for benign input. Low risk is below 0.3, medium risk starts at 0.3, high risk starts at 0.6, and critical risk starts at 0.8. The associated defense policy allows low-risk interactions, monitors medium-risk interactions, restricts high-risk interactions, and blocks critical-risk interactions.

The experimental evidence supports two conclusions. First, learned classification can detect a broader set of phrases in the synthetic dataset than the current rule/heuristic implementation. Second, the rule-based detector has stronger precision on the evaluated examples but unacceptable injection recall if it is used without another control. The adaptive live system therefore benefits from layered detection and cumulative-risk state rather than relying on a single binary decision.

Actual injection success is not claimed from the offline metrics. A false-negative detector result indicates pass-through, not that the injected text successfully changed model behavior or caused a security violation. Conversely, a blocked request may be safe or harmful. Human adjudication and end-to-end testing are required for valid success-rate measurement.

## 10. Limitations & Future Work

One limitation is that the current evaluation dataset is small and synthetic, with only 48 balanced samples. It may not represent real conversations, obfuscated attacks, indirect injections, multilingual inputs, or adversarially generated prompt variations.

Additional limitations and future improvements include:

- Add human-adjudicated end-to-end outcomes for measuring actual injection success rather than only detector pass-through.
- Expand the dataset with real and adversarial examples, indirect prompt injection, multilingual text, and multiple-turn attack sequences.
- Evaluate the live detector and cumulative-risk policy through controlled integration tests.
- Measure latency and resource use in a deployed environment under concurrent user load.
- Add calibrated confidence thresholds and tune the precision-recall trade-off for operational requirements.
- Explore model-based embeddings, retrieval, and ensemble methods while retaining explainable signals.
- Add privacy-preserving retention and redaction controls for conversation histories and security events.
- Add external-service failure handling and test behavior when MongoDB, SMTP, Google authentication, or the LLM endpoint is unavailable.

## 11. Conclusion

PI-EWS demonstrates a layered approach to prompt-injection defense that combines live heuristic detection, cumulative risk assessment, adaptive response policies, and persistent security-investigation information. The experimental comparison shows that the current rule/heuristic baseline is highly precise on the available synthetic dataset but misses most injection samples, while a TF-IDF logistic-regression detector detects all injected samples but introduces false positives.

The defense architecture should not interpret these offline metrics as proof of real-world resistance. The live system's layered policy and conversation-level state can reduce the likelihood of repeated or escalating attacks, but it requires broader datasets, real-world telemetry, and human-adjudicated end-to-end testing before deployment decisions can be finalized. Future work should strengthen data diversity, threshold calibration, end-to-end evaluation, and operational monitoring while preserving explainability and role-based investigation controls.

## 12. References

1. Project source and implementation documentation: PI-EWS repository, `PROJECT_HLD.md`.
2. Implementation verification and feature checklist: PI-EWS repository, `IMPLEMENTATION_CHECKLIST.md`.
3. Offline experiment protocol and recorded metrics: PI-EWS repository, `backend/experiments/results.json`.
4. Dataset structure and labeling documentation: PI-EWS repository, `backend/datasets/README.md`.
