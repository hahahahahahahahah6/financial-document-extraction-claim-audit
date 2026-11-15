# Documentation claim auditor

An offline static auditor comparing documentation promises with source call patterns.
It reads root README.md and Markdown with a docs path component, excludes fenced
code, and parses source without executing it. Audits make no network calls,
write no files, and collect no telemetry.

## Install and use

```sh
python3 -m pip install .
financial-document-extraction-claim-audit audit . --json
python3 -m financial_document_extraction_claim_audit audit . --verbose
financial-document-extraction-claim-audit audit . --ignore vendor --ignore build --fail-on medium
financial-document-extraction-claim-audit --version
python3 -m unittest discover
python3 -m build
```

The optional repository defaults to the current directory. Ignore prefixes match
whole relative path components and can be repeated. Exit codes: 0 for PASS or
findings below threshold, 2 for findings at or above threshold, 1 for usage or
I/O errors. The default threshold is high; medium also fails on test-only evidence.
JSON includes verdict, findings with message and severity, claims, and evidence.
Verbose text includes locations. There is at most one finding per claim family.

## Rules and vocabulary

A positive promise without production evidence produces HIGH, or MEDIUM when
only tests contain evidence. A denial contradicted by production evidence produces
HIGH. A positive promise with no source fails; a denial with no source passes.

```text
documented-financial-document-extraction-claim-false
documented-no-financial-document-extraction-claim-false
financial document extraction
extract financial document
extracts financial document
extracting financial document
financial document parsing
financial document parser
parse financial document
parses financial document
financial document scanning
financial document scanner
scan financial document
scans financial document
financial documents extraction
extract financial documents
extracts financial documents
extracting financial documents
financial documents parsing
financial documents parser
parse financial documents
parses financial documents
financial documents scanning
financial documents scanner
scan financial documents
scans financial documents
financial paperwork extraction
extract financial paperwork
extracts financial paperwork
extracting financial paperwork
financial paperwork parsing
financial paperwork parser
parse financial paperwork
parses financial paperwork
financial paperwork scanning
financial paperwork scanner
scan financial paperwork
scans financial paperwork
financial document data extraction
extract financial document data
extracts financial document data
extracting financial document data
financial documents data extraction
extract financial documents data
extracts financial documents data
extracting financial documents data
financial document field extraction
extract financial document fields
extracts financial document fields
extracting financial document fields
financial documents field extraction
extract financial documents fields
no financial document extraction
does not extract financial document
does not support financial document extraction
without financial document extraction
no financial document parser
does not parse financial document
no financial document scanner
financial document extraction not supported
no financial documents extraction
does not extract financial documents
does not support financial documents extraction
without financial documents extraction
no financial documents parser
does not parse financial documents
no financial documents scanner
financial documents extraction not supported
no financial paperwork extraction
does not extract financial paperwork
does not support financial paperwork extraction
without financial paperwork extraction
no financial paperwork parser
does not parse financial paperwork
no financial paperwork scanner
financial paperwork extraction not supported
```

Paragraphs are split on blank lines, lowercased, contractions expanded, hyphens
replaced by spaces, and whitespace collapsed. Exact phrases use word boundaries,
longest first with alphabetical ties. Denial spans are removed before positive
matching. Inline code counts. Backtick and tilde fences with up to three leading
spaces do not count. Symlinks are excluded. Source under fixtures, docs, or examples
is excluded; tests, test_*.py and *_test.py count separately. Invalid syntax gives
no evidence. Each route must occur in one module. Imports resolve aliases; local
functions, methods, classes and assignment/context-manager bindings shadow names.

## Evidence routes

Only the following two routes count. The product argument is an exact Name or
Attribute suffix, in any positional or keyword argument. The parse receiver need
not be the constructed client. The module must import Mindee in some form.

```text
mindee.Client() + any_receiver.parse(FinancialDocumentV1, source)
from mindee import Client as C; C() + receiver.parse(product.FinancialDocumentV1, source)
extract_financial_document
parse_financial_document
extract_financial_documents
parse_financial_documents
financial_document_extraction
financial_document_extractor
financial_document_parser
extract_financial_paperwork
parse_financial_paperwork
financial_paperwork_extraction
financial_paperwork_extractor
financial_paperwork_parser
extract_financial_document_data
parse_financial_document_data
financial_document_data_extraction
extract_financial_document_fields
parse_financial_document_fields
financial_document_field_extraction
extract_financial_documents_data
parse_financial_documents_data
financial_document_scan
financial_document_scanner
scan_financial_document
scan_financial_documents
```

Generic attributes count on any base. Bare calls require a matching from-import
or import alias. Bare references, imports, comments, and strings do not count.

## Product scope and limitations

The checked capability covers invoices, credit notes, credit card receipts, and
expense receipts. It does not cover bank statements, tax forms, or pay stubs.
The field inventory and SDK facts from the supplied specification follow.

```text
mindee Client construction + parse call passing FinancialDocumentV1
(Name exactly FinancialDocumentV1, or Attribute with attr exactly
FinancialDocumentV1 such as product.FinancialDocumentV1 /
mindee.product.FinancialDocumentV1 /
mindee.product.financial_document.FinancialDocumentV1) as any
argument; import gate mindee. FinancialDocumentV1 is NOT a 4.x-only
fingerprint (4.22.0 wheel inspected 2026-11-15:
mindee/product/financial_document/financial_document_v1.py
defines class FinancialDocumentV1(Inference), endpoint_name
"financial_document", endpoint_version "1", exported at top-level
mindee.product and via mindee.product.financial_document; its
document is "Financial Document API version 1" with fields
billing_address, category, customer_address,
customer_company_registrations, customer_id, customer_name, date,
document_number, document_type (INVOICE / CREDIT NOTE / CREDIT CARD
RECEIPT / EXPENSE RECEIPT), document_type_extended, due_date,
invoice_number, line_items, locale, payment_date, po_number,
receipt_number, reference_numbers, shipping_address, subcategory,
supplier_address, supplier_company_registrations, supplier_email,
supplier_name, supplier_payment_details, supplier_phone_number,
supplier_website, taxes, time, tip, total_amount, total_net,
total_tax; there is NO FinancialDocumentV2 and no
TypeFinancialDocumentV1 form — the 4.22.0 wheel has no
mindee/documents module; the 5.4.0 wheel inspected 2026-11-15 still
contains it at mindee/v1/product/financial_document/ — the product
survived in 5.x, unlike the material certificate / energy bill /
delivery note / bill of lading / resume / US mail products). The tool
detects the call in source, not the installed SDK version. A parse
call passing any other product (InvoiceV4, ReceiptV5,
PassportV1, BankCheckV1, BankAccountDetailsV1,
BankAccountDetailsV2, PayslipV2, PayslipV3, NutritionFactsLabelV1, HealthcareCardV1,
BusinessCardV1, CustomV1, GeneratedV1, BillOfLadingV1, ResumeV1,
DeliveryNoteV1, DriverLicenseV1, IdCardV1, InternationalIdV2,
CarteGriseV1, EnergyBillV1, MaterialCertificateV1, BarcodeReaderV1, CropperV1, UsMailV2, UsMailV3, or any other)
is NOT evidence.
```

The following notes explain exclusions and false-positive risks. They describe
static matching rather than a guarantee of runtime success or configured credentials.

```text
- The bare phrases "financial paperwork extraction" / "extract
  financial paperwork" / "financial paperwork parsing" / "financial
  paperwork parser" are deliberately FINANCIALDOCUMENTEXTRACTION
  phrases: in document-tool docs they almost always name financial
  document extraction. But "financial paperwork" can also name a
  record the tool merely stores, displays, or manages (a paperwork
  archive, a document vault, a filing cabinet) without extracting
  fields from a financial document: a doc that means storing,
  displaying, or managing paperwork, not extracting fields from it,
  is a false positive; the tool flags the claim, only the code
  decides.
- "financial document data extraction" / "extract financial document
  data" are deliberately phrases: "financial document data" is the
  common short name for the structured fields pulled from a financial
  document. But "financial document data" can also name data about
  documents rather than fields from them (a document count, a
  processing log, a storage report): a doc that means document
  metadata, not field extraction from a financial document, is a
  false positive; the tool flags the claim, only the code decides.
- "financial document scanning" / "scan financial document" are
  deliberately phrases: "scanning" a financial document can mean
  merely photographing a page or OCRing it into raw text, with no
  structured field extraction. The tool flags the claim; only the
  code decides.
- "financial document parsing" / "financial document parser" are
  deliberately phrases: a doc can say "financial document parser"
  about a tool that only renders a document as formatted text, or a
  "financial document parser" that is really a keyword highlighter
  over plain text. The tool flags the claim; only the code decides.
- "financial document field extraction" / "extract financial document
  fields" are deliberately phrases: extracting named fields is the
  core of this family. But a doc can say "financial document fields"
  about a form builder (fields the user fills in) rather than fields
  extracted from a document: a doc that means creating a form, not
  extracting fields from a document, is a false positive; the tool
  flags the claim, only the code decides.
- "financial document" can also name a document class in general
  ("financial documents include invoices, statements, and tax forms")
  rather than the extraction operation — but the phrase lists require
  an extraction / parsing / scanning verb, so a bare class mention is
  not a phrase. Say so in the README.
- FinancialDocumentV1 carries the field set listed in the mindee
  names section above (document type, document / invoice / receipt
  numbers, dates, customer and supplier details, line items, taxes,
  totals, tip): it has no bank-statement fields (no account number,
  no statement period, no transactions with running balance), no
  pay-stub fields, and no tax-form fields. A tool that extracts those
  does so through some other route; this family checks for the
  FinancialDocumentV1 call, not for those fields. Say so in the
  README.
- A generic `extract_financial_document(` / `parse_financial_document(` /
  `extract_financial_documents(` / `extract_financial_paperwork(` call can
  name a string parser for text the user typed in rather than a
  document extractor: the tool counts the call, the claim plus
  the code decide — and a subprocess call invoking an external CLI
  is NOT evidence by design, so a thin wrapper that only calls
  subprocess fails.
- Mindee `parse` with FinancialDocumentV1 counts as evidence: the
  product exists in mindee 4.22.0 (wheel inspected 2026-11-15). The
  tool detects the call in source, not whether the call succeeds
  against a current API version. Say so in the README.
- Mindee `parse` with FinancialDocumentV1 is NOT a 4.x-only
  fingerprint: unlike the material certificate / energy bill /
  delivery note / bill of lading / resume / US mail products, mindee
  5.x kept the financial document product (5.4.0 wheel inspected
  2026-11-15 — it is still present at
  mindee/v1/product/financial_document/). Say so in the README.
- Mindee `parse` with InvoiceV4 / ReceiptV5 / PassportV1 /
  BankCheckV1 / BankAccountDetailsV1 /
  BankAccountDetailsV2 / PayslipV2 / PayslipV3 / NutritionFactsLabelV1 /
  HealthcareCardV1 / BusinessCardV1 / CustomV1 / GeneratedV1 /
  BillOfLadingV1 / ResumeV1 / DeliveryNoteV1 / DriverLicenseV1 /
  IdCardV1 / InternationalIdV2 / CarteGriseV1 / EnergyBillV1 /
  MaterialCertificateV1 / BarcodeReaderV1 / CropperV1 / UsMailV2 /
  UsMailV3 is NOT detected: those are other document types. Say so in
  the README.
- Mindee `parse` with InvoiceV4 alone is NOT detected even though an
  invoice is a financial document: the generic claim promises more
  than invoices, and the invoice-only route is the invoice family's
  domain. The same holds for ReceiptV5 alone. Say so in the README.
- Mindee `parse` with BarcodeReaderV1 is NOT detected: reading a
  barcode is a different operation from extracting financial document
  fields, even though a receipt may carry a barcode as an
  identifier. Say so in the README.
- Azure `begin_analyze_document` with ANY model id is NOT
  detected: Azure Document Intelligence has no financial document model (the
  Learn v4.0 GA prebuilt-model pages list no such model, verified
  2026-11-15). Say so in the README.
- Veryfi calls of ANY kind are NOT detected: veryfi has no financial document
  method (5.1.0 wheel inspected 2026-11-15 — the word "financial" does
  not appear anywhere in the wheel), and its document APIs post to a
  generic documents endpoint shared across document types. Say so in
  the README.
- Google Document AI `process_document` / `batch_process_documents`
  with ANY processor is NOT detected: Document AI has no financial document
  processor (the processors list page contains no such processor,
  verified 2026-11-15). Say so in the README.
- Eden AI universal-ai calls with ANY model id are NOT detected:
  Eden AI does document a financial parser
  (`ocr/financial_parser/{provider}`), but the model id is a plain
  string inside an arbitrary request payload, not a typed SDK call,
  so there is no fixed static fingerprint for the call itself. Say
  so in the README.
- LlamaParse calls are NOT detected: its parsing API is
  generative with no fixed static fingerprint naming financial document.
  Say so in the README.
- Nanonets / Docsumo / ABBYY Vantage / Rossum / Klippa / Parseur /
  Extend calls are NOT detected: opaque model / skill / queue /
  template / workflow IDs, or a generic upload endpoint with the
  document type configured outside the call — no fixed fingerprint.
  Say so in the README.
- Textract `analyze_document` / `analyze_expense` / `analyze_id` /
  `start_document_analysis` / `get_expense_analysis` are NOT
  detected: generic document, expense, and identity analysis are
  not financial document extraction, and Textract has no financial document operation.
  Say so in the README.
- Generic "document extraction" calls (extract_document /
  parse_document / document_extraction with no "financial" qualifier)
  are NOT detected: a bare document call could name extraction from
  any document, not financial document extraction. Say so in the
  README.
- Financial statement extraction calls (extract_financial_statement /
  parse_financial_statement / financial_statement_extraction) are NOT
  detected: a financial statement is a balance sheet, income
  statement, or cash-flow statement, a different document from the
  invoices, credit notes, and receipts this family covers. Say so in
  the README.
- Email extraction calls (extract_email / parse_email /
  email_extraction) are NOT detected: email is a different medium
  from a financial document. Say so in the README.
- A hand-rolled extraction from OCR text (`re.search` /
  `re.findall` on extracted text plus manual field assembly, no
  listed call) is NOT detected: the tool requires a listed call.
  Say so in the README.
- The mindee CLI, the veryfi CLI, and any other external financial document
  tool invoked through subprocess are NOT detected: subprocess
  calls invoking an external CLI are NOT evidence by design. Say so
  in the README.
- Azure Document Intelligence, Mindee, and Veryfi are cloud APIs:
  the tool detects the client call in source, not whether
  credentials are configured or the call succeeds. Say so in the
  README.
- "extract financial statement" / "financial statement extraction" /
  "extract balance sheet" / "balance sheet extraction" claims are NOT
  in the phrase lists: a financial statement is a different document
  from the invoices, credit notes, and receipts this family covers.
  Say so in the README.
- "extract email" / "email extraction" / "extract emails" claims
  are NOT in the phrase lists: email extraction is a different
  medium from financial document extraction. Say so in the README.
- "extract financial document text" / "extract text from financial document" claims are
  NOT in the phrase lists: extracting plain text from a financial document
  is text extraction, not financial document field extraction. Say so in the
  README.
- "financial document management" / "financial document storage" /
  "financial document archiving" claims are NOT in the phrase lists:
  storing or managing financial documents is a different operation
  from extracting fields from one. Say so in the README.
- "financial document automation" / "financial document workflow"
  claims are NOT in the phrase lists: automating a workflow around
  financial documents is a different operation from extracting fields
  from a financial document. Say so in the README.
- Invoice extraction claims ("extract invoices", "invoice
  extraction"), receipt extraction claims ("extract receipts",
  "receipt extraction"), ID document extraction claims ("extract
  passports", "passport extraction"), bank check extraction claims
  ("extract bank checks", "check extraction"), bank statement
  extraction claims ("extract bank statements", "statement
  extraction"), tax form extraction claims ("extract tax forms",
  "extract w2 forms", "1099 extraction"), pay stub extraction
  claims ("extract pay stubs", "payslip extraction"), health
  insurance card extraction claims ("extract health insurance
  cards", "health insurance card extraction"), business card
  extraction claims ("extract business cards", "business card
  extraction"), credit card extraction claims ("extract credit
  cards", "credit card extraction"), contract extraction claims
  ("extract contracts", "contract extraction"), mortgage
  extraction claims ("extract mortgages", "mortgage extraction"),
  resume extraction claims ("extract resumes", "resume
  extraction"), bill of lading extraction claims ("extract
  bills of lading", "bill of lading extraction"), delivery
  note extraction claims ("extract delivery notes", "delivery
  note extraction"), carte grise extraction claims ("extract
  carte grises", "carte grise extraction"), energy bill extraction
  claims ("extract energy bills", "energy bill extraction"),
  marriage certificate extraction claims ("extract marriage
  certificates", "marriage certificate extraction"), bank
  account details extraction claims ("extract bank account details",
  "bank details extraction", "rib extraction"), nutrition
  facts label extraction claims ("extract nutrition facts labels",
  "nutrition facts label extraction"), material certificate
  extraction claims ("extract material certificates", "material
  certificate extraction", "extract mill test certificates",
  "mill test certificate extraction"), and US mail extraction claims
  ("extract us mail", "us mail extraction", "extract usps mail",
  "usps mail extraction") are NOT in
  the phrase lists: this family covers financial documents only.
  Say so in the README.
- As with every family: static pattern matching, not semantic
  judgement; dead code counts; alias chains the tracer cannot follow
  are missed; exact phrases only, not semantics; denial handling
  depends on the denial phrase list; each route must sit in a single
  module.
```
