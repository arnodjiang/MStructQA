# Architecture and research framing

The **harness** is the runnable system: immutable source identity → recovered structured data and source-language Python → shared translation dictionary → code specialization → raster rendering → mechanical validation → candidate artifact. The **skill** is the agent-facing procedure for preparing new inputs, choosing a recovery method and inspecting outcomes. An **agent** executes that procedure; multiple agents are optional and do not constitute the core method.

For an open-source research implementation, keep executable harness code as the primary contribution and distribute the skill with it. Preserve prompts, schemas, original and localized code, translation provider/model metadata, configuration, hashes, dataset provenance and uncertainty. Do not publish API keys, downloaded datasets or proprietary fonts as part of this code license.

Potential method components to evaluate (not established novelty claims):

1. Numeric/structural invariance across languages: data and cell geometry are frozen while only label bindings change.
2. Coupled visual and QA localization: protected references bind the question to the exact localized visible label.
3. Reproducible code specialization: every language retains standalone executable source, allowing audits and regeneration.
4. Separate reconstruction and language errors: English/source reconstruction is reviewed before multilingual comparison; ambiguity prevents automatic benchmark admission.

Useful ablations: QA-only translation with original English image; independently translated QA/image labels; shared label binding; optional image text replacement baseline; code reconstruction with/without fidelity filtering. Measure reconstruction answer preservation using declared upstream scoring rules, human bilingual semantic fidelity, missing/clipped labels, label ambiguity, and task accuracy broken down by source, task and language. Include macro-averaged per-source/per-language results and confidence intervals grouped by source figure, not treating language variants as independent draws.

Pixel traces can merge close-color series; log axes, occlusion and low-resolution marks cause systematic errors. A shared incorrect reconstruction can be perfectly consistent across languages while still invalidating the QA. Font coverage checks do not prove Arabic bidi or translation correctness. Numerical answer equivalence involving translated units must be reviewed. Distinguish source-level fidelity, rendering validity, language validity and final benchmark admission in any paper.

Current 5-case MVisQA pilot is a feasibility example, not evidence of general recovery success. In particular the recovered hopper:stand point differs from its original approximate reference; retain that case as pending rather than treating a custom tolerance as an official pass. Establish research novelty through a related-work comparison and measured ablations, not by calling a workflow a skill or an agent.
