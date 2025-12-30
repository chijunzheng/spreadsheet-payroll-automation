# Payroll Time Validation PRD

## Introduction/Overview
Build a validation tool that compares raw punch data from a `.csv` file against a manually filled payroll `.xlsx` spreadsheet. The tool applies company rounding rules to the raw punches, flags any discrepancies between the computed (expected) times and the spreadsheet values, and writes a per-employee validation status into the `.xlsx`. The goal is to catch manual entry errors so the company does not overpay or underpay based on early/late punches and lunch break rules.

## Goals
- Detect mismatches between raw punch data (after applying rounding rules) and the recorded payroll spreadsheet values.
- Provide a clear, actionable error report that pinpoints employee, date, field, expected value, and actual value.
- Mark each employee block in the `.xlsx` as `ok` or `needs attention` in the designated status cell.
- Avoid modifying recorded time values in the `.xlsx`.

## User Stories
- As a payroll admin, I want to upload a punch `.csv` and a filled payroll `.xlsx` so I can validate that recorded times follow company rules.
- As a payroll admin, I want to see a list of discrepancies with expected values so I can correct the payroll sheet.
- As a payroll admin, I want the tool to flag missing or extra entries so I can investigate data issues.

## Functional Requirements
1. The system must accept two inputs: a punch `.csv` file and a filled payroll `.xlsx` file.
2. The system must parse employee identifiers and dates from both files to align records by employee and day.
3. The system must group punches by employee and date and identify the daily sequence of punches (start work, lunch out, lunch in, end of day).
4. The system must support exactly one lunch break per day and flag days with missing or extra punches that prevent identifying the expected sequence.
5. The system must compute expected paid times from the `.csv` using these rules:
6. The system must treat early clock-in as rounding up to the next 30-minute boundary.
7. The system must keep late clock-in as the actual punch-in time.
8. The system must treat clock-out for lunch as the actual punch-out time or a rounding up to the next 30-minute boundary when early.
9. The system must enforce a 30-minute lunch break:
10. The system must set early lunch return to exactly 30 minutes after lunch-out.
11. The system must keep late lunch return as the actual punch-in time.
12. The system must treat end-of-day clock-out as the actual punch-out time (no rounding).
13. The system must allow the “no lunch punches” edge case: if the raw data has a single IN/OUT pair and the shift duration exceeds 6 hours, the system must accept a manually entered 30-minute lunch in the `.xlsx` as valid.
14. The system must compare each expected time to the corresponding value in the `.xlsx`.
15. The system must flag discrepancies and output them in a validation report.
16. The system must flag missing employee/date rows in either file.
17. The system must locate each employee status cell in column `H` on the row where column `F` contains `Total` or `total`.
18. The system must write `ok` to the status cell when no discrepancies exist for that employee, otherwise write `needs attention`.
19. The system must output an updated `.xlsx` (copy) with status cells filled while leaving all time entry cells unchanged.
20. The system must provide a user-friendly interface to upload the `.csv` and `.xlsx` without requiring command-line usage.
21. The system must provide download links for both the validation report and the validated `.xlsx` output.

## Non-Goals (Out of Scope)
- Automatically correcting or rewriting the timesheet time entries in the `.xlsx`.
- Generating payroll totals, overtime calculations, or wage computations.
- Importing data from time clocks or HR systems beyond the provided files.

## Design Considerations (Optional)
- Provide a simple local web page for file upload and output download.
- The validation report can be a `.csv` or `.xlsx` file with columns: employee, date, field, expected, actual, error_type.
- The updated timesheet output should be saved as a new file (e.g., `*-validated.xlsx`) to avoid overwriting the original.

## Technical Considerations (Optional)
- The `.xlsx` is a filled spreadsheet maintained by another employee; assume its structure is consistent but not necessarily a strict template.
- Employee identifiers and date formats must be normalized (e.g., trimming whitespace, consistent date parsing).
- Time zone handling should be clarified if punches span midnight or include time zones.
- The example `.csv` includes a report header row and a date-range row before column headers.
- The example `.xlsx` stores dates as Excel serial numbers and times as fractional days; comparisons should normalize to a consistent time representation.
- The `.xlsx` layout uses columns `B`–`G` for Monday–Saturday; rows labeled `Clock In`, `Clock Out (Lunch)`, `Clock In (Work)`, and `Clock Out` in column `A` contain the times for each day.
- The `.xlsx` contains non-time rows (e.g., `OVERTIME`, `TOTAL HRS`, notes); these should be ignored for validation.
- Status cells for each employee block are in column `H` on rows where column `F` is `Total` (case-insensitive), matching examples like `H15`, `H29`, and `H45`.

## Success Metrics
- 100% of discrepancies between expected and recorded times are reported.
- Payroll admins can resolve errors without manual cross-checking of every row.
- Validation report generation completes within a few seconds for a typical payroll period.
- All employee blocks receive a status value (`ok` or `needs attention`) in the output `.xlsx`.

## Open Questions
- None.
