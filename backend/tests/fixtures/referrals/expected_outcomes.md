# Synthetic referral examples

These are fictional administrative examples, not institutional policy. The text
packets are for manual inspection; the API accepts structured JSON, not documents.

| Packet | Expected human review | Expected API behavior |
| --- | --- | --- |
| `complete.txt` | All five required fields are present. | Transcribe the values and submit; expect `201`, then `200` when retrieving the assigned ID. |
| `missing_information.txt` | Referring organization is missing; obtain it before entry. | Omitting `referring_organization`, or supplying a blank value, returns `422`. |
| `conflicting_information.txt` | DOB differs between the letter and attachment; clarify before entry. | Conflict detection is not implemented. Either individually valid date would be accepted; the coordinator must resolve the discrepancy. |

The API does not assess packet completeness, verify the truth of submitted values,
or approve referrals. Creation only registers the manually entered information.

## Automated extraction baseline

The same packets now exercise `RuleBasedExtractor` in `test_extractions.py`.
The complete packet produces five found fields. The incomplete packet retains a
null referring organization and a missing finding. The conflicting packet retains
both DOB candidates with their evidence, selects neither, and reports a conflict.
These findings come only from attached source text, independent of manual values.
