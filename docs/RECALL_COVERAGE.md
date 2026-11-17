# Reviewed recall coverage

Automatic verification currently supports the baseline NEWDERY notice 26-792. With P1 enabled and CPSC live mode selected, reviewed normalizers also support Flaunt 26-610, iStore 25-390 and Baseus 25-248. Discovered notices outside this catalog, changed records, and unknown restrictions require review.

## Baseus 25-248

The [official CPSC notice](https://www.cpsc.gov/Recalls/2025/Baseus-Portable-Chargers-Recalled-Due-to-Fire-Hazard-Sold-on-Amazon-com-by-Shenzhen-Baseus-Technology) identifies model BS-30KP365 and serials ending in ASCII digits 0–9 or uppercase D. Its serial label begins SN. Replacement units ending A are excluded. The model comparison preserves punctuation and suffixes. Supported family wording is power bank or portable charger, with brand Baseus.

Import the full printed serial using the optional CSV column serial_number. Keep leading zeros and the SN prefix. A missing or empty serial stays unknown. Existing serial_prefix retains its separate prefix semantics. The ordinary recorded demo still exercises the original five fixtures; Baseus acceptance uses the captured official response through the live adapter in offline tests.

The normalizer pins the entire reviewed API record and its CPSC URL. It preserves the replacement remedy and official safety wording, including disposal cautions, without prefilling disposal confirmation. Photograph requirements remain conditional where the notice makes them conditional. An order receipt is not invented as mandatory proof.

Source acquisition metadata and the fresh public lookup result are in docs/evidence/recall-coverage. The public lookup exercised the adapter and matcher with synthetic facts. Import/run/evidence/local review/export acceptance uses recorded HTTP responses. Source monitoring uses the registered public Baseus query and revokes approval when the source changes or becomes unavailable.

INIU 26-135 remains review-only. On acquisition its CPSC API remedy concerned a Grizzly planer while the official INIU webpage described a refund. VC Group 25-190 also remains review-only pending purchase-order restriction support. This coverage catalog supports a bounded set of notices; it does not establish comprehensive discovery or personal remedy entitlement.
