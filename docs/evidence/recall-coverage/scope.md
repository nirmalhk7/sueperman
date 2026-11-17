# Issue 5 bounded coverage decision

Recorded before runtime implementation. This increment selects one notice, Baseus 25-248. Exact model BS-30KP365 and a complete serial number ending in ASCII 0–9 or uppercase D are supported. A replacement serial ending A is excluded. Missing serial numbers stay unknown. No model punctuation or suffix aliases are introduced. Brand Baseus and source-reviewed family wording power bank / portable charger are required.

Add an optional serial_number field to ProductInput and CSV import. Existing serial_prefix has prefix semantics and cannot represent a complete serial reliably. Add one structured serial_number condition with explicit allowed suffixes. Full CPSC record and URL pins remain mandatory. Changed or conflicting official records stay unverified. API normalizer tests will exercise exact and near models, missing and excluded serials, changed source records, optional flag boundaries, and upload/run/evidence/review/export with recorded HTTP responses. Existing five outcomes and stale approval checks remain required regression coverage.

INIU 26-135 was considered and deferred. The acquired API record incorrectly supplied Grizzly planer repair-kit text while its official webpage described an INIU refund. No positive normalizer is added for this inconsistent record. VC Group 25-190 remains deferred because its purchase-order restrictions need separate representation.

Expected changes are p1 normalizer catalog/dispatch, ProductInput, CSV extractor, restriction matcher, coverage documentation, and a short dashboard coverage statement. Verification includes behavior-first targeted tests, full backend/frontend regressions, browser regression, lint, types, build and smoke. No paid provider required.
