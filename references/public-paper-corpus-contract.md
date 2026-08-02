# Public robotics paper corpus contract

The balanced 100-paper index is a local-only build input. It is intentionally
not committed to Git:

~~~text
corpus/public-paper-index.json
~~~

The tracked derivative is:

~~~text
corpus/robotics-research-runtime.v1.json
~~~

Normal routing reads only that compact runtime artifact. Paper PDFs, extracted
text, embeddings, paper-level signatures, and other paper-level intermediates
remain local caches or offline build products.

## Offline corpus constraints

The local index must satisfy:

- 100 records total;
- 50 journal and 50 conference records;
- conference presentation level oral or above;
- at least 51 award-recognized records, preserving winner/finalist status;
- balanced primary-axis coverage across E/P/C/L/D/H/A/S;
- public preprint and final-publication URLs.

These constraints govern the offline corpus and runtime rebuild. They are not
runtime acceptance signals, prevalence estimates, or statistical PCA/factor
analysis.

## Build and audit

~~~text
python scripts/validate_public_paper_index.py <local-corpus>
python scripts/build_robotics_research_runtime.py --input <local-corpus>
python scripts/validate_robotics_research_runtime.py
~~~

The input can also be provided through ROBOTICS_CORPUS_PATH. The builder stores
the source SHA-256, source count, axis counts, and compact exemplars in the
runtime artifact. It does not store the full paper records in the runtime
artifact and does not require the source path to exist later.

The calibrator is also offline-only:

~~~text
python scripts/calibrate_robotics_submanifold.py --input <local-corpus>
~~~

The runtime artifact retains the ResearchStudio pattern summary, the
eight-axis strategy rows, compact evidence boundaries, and the closed outcome
contract. It retains no raw full text.

## Provenance and receipts

Public source manifests, text-coverage receipts, and web-fulltext receipts can
remain tracked because they are provenance summaries rather than the corpus
itself. Downloaded PDFs and extracted text stay under ignored local cache
directories.

The ResearchStudio signature and clustering builders remain available for an
explicit offline rebuild. Their outputs are not normal runtime dependencies.
When a new corpus version is built, rebuild and validate the runtime artifact
before using it.

## Non-claims

The corpus is a balanced research-reference sample. It does not estimate field
prevalence, venue acceptance probability, or causal effects of awards and
presentation categories. Model-simulated pattern induction does not claim real
UMAP/HDBSCAN or statistical factor fitting.
