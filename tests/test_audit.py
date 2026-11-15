import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from financial_document_extraction_claim_audit import phrases
from financial_document_extraction_claim_audit.audit import audit, module_evidence, claims_in
from financial_document_extraction_claim_audit.__main__ import main

EXPECTED_POSITIVE = ('financial document extraction', 'extract financial document', 'extracts financial document', 'extracting financial document', 'financial document parsing', 'financial document parser', 'parse financial document', 'parses financial document', 'financial document scanning', 'financial document scanner', 'scan financial document', 'scans financial document', 'financial documents extraction', 'extract financial documents', 'extracts financial documents', 'extracting financial documents', 'financial documents parsing', 'financial documents parser', 'parse financial documents', 'parses financial documents', 'financial documents scanning', 'financial documents scanner', 'scan financial documents', 'scans financial documents', 'financial paperwork extraction', 'extract financial paperwork', 'extracts financial paperwork', 'extracting financial paperwork', 'financial paperwork parsing', 'financial paperwork parser', 'parse financial paperwork', 'parses financial paperwork', 'financial paperwork scanning', 'financial paperwork scanner', 'scan financial paperwork', 'scans financial paperwork', 'financial document data extraction', 'extract financial document data', 'extracts financial document data', 'extracting financial document data', 'financial documents data extraction', 'extract financial documents data', 'extracts financial documents data', 'extracting financial documents data', 'financial document field extraction', 'extract financial document fields', 'extracts financial document fields', 'extracting financial document fields', 'financial documents field extraction', 'extract financial documents fields')
EXPECTED_NEGATIVE = ('no financial document extraction', 'does not extract financial document', 'does not support financial document extraction', 'without financial document extraction', 'no financial document parser', 'does not parse financial document', 'no financial document scanner', 'financial document extraction not supported', 'no financial documents extraction', 'does not extract financial documents', 'does not support financial documents extraction', 'without financial documents extraction', 'no financial documents parser', 'does not parse financial documents', 'no financial documents scanner', 'financial documents extraction not supported', 'no financial paperwork extraction', 'does not extract financial paperwork', 'does not support financial paperwork extraction', 'without financial paperwork extraction', 'no financial paperwork parser', 'does not parse financial paperwork', 'no financial paperwork scanner', 'financial paperwork extraction not supported')
EXPECTED_GENERIC = ('extract_financial_document', 'parse_financial_document', 'extract_financial_documents', 'parse_financial_documents', 'financial_document_extraction', 'financial_document_extractor', 'financial_document_parser', 'extract_financial_paperwork', 'parse_financial_paperwork', 'financial_paperwork_extraction', 'financial_paperwork_extractor', 'financial_paperwork_parser', 'extract_financial_document_data', 'parse_financial_document_data', 'financial_document_data_extraction', 'extract_financial_document_fields', 'parse_financial_document_fields', 'financial_document_field_extraction', 'extract_financial_documents_data', 'parse_financial_documents_data', 'financial_document_scan', 'financial_document_scanner', 'scan_financial_document', 'scan_financial_documents')


GOOD = 'import mindee\nclient = mindee.Client()\nclient.parse(product.FinancialDocumentV1, source)'
POS_RULE = 'documented-financial-document-extraction-claim-false'
NEG_RULE = 'documented-no-financial-document-extraction-claim-false'


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['audit', str(self.root), *args])
        return code, output.getvalue()

    def test_phrase_oracle(self):
        tree = ast.parse(Path(phrases.__file__).read_text())
        values = {node.targets[0].id: ast.literal_eval(node.value)
                  for node in tree.body if isinstance(node, ast.Assign)}
        self.assertEqual(values['FINANCIALDOCUMENTEXTRACTION'], EXPECTED_POSITIVE)
        self.assertEqual(values['NOFINANCIALDOCUMENTEXTRACTION'], EXPECTED_NEGATIVE)
        self.assertEqual(values['GENERIC_NAMES'], EXPECTED_GENERIC)
        self.assertEqual(len(set(EXPECTED_GENERIC)), 24)

    def test_good(self):
        self.write('README.md', 'We extract financial documents.')
        self.write('main.py', GOOD)
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(audit(self.root)['verdict'], 'PASS')

    def test_bad_high(self):
        self.write('README.md', 'Financial document extraction')
        self.write('main.py', 'print("hi")')
        code, output = self.run_cli('--json')
        self.assertEqual(code, 2)
        result = json.loads(output)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertEqual(result['findings'], [{'rule': POS_RULE, 'severity': 'HIGH',
                                             'message': 'Documented capability has no production evidence.'}])

    def test_test_only(self):
        self.write('README.md', EXPECTED_POSITIVE[0])
        self.write('tests/sample.py', GOOD)
        self.assertEqual(self.run_cli()[0], 0)
        self.assertEqual(self.run_cli('--fail-on', 'medium')[0], 2)
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'MEDIUM')

    def test_denial(self):
        self.write('README.md', EXPECTED_NEGATIVE[0])
        self.write('main.py', GOOD)
        self.assertEqual(self.run_cli()[0], 2)
        self.assertEqual(audit(self.root)['findings'][0]['rule'], NEG_RULE)
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'HIGH')

    def test_no_claim(self):
        self.write('README.md', 'An audit helper.')
        self.write('main.py', GOOD)
        self.assertEqual(self.run_cli()[0], 0)

    def test_no_source_positive(self):
        self.write('README.md', EXPECTED_POSITIVE[0])
        self.assertEqual(self.run_cli()[0], 2)

    def test_no_source_denial(self):
        self.write('README.md', EXPECTED_NEGATIVE[0])
        self.assertEqual(self.run_cli()[0], 0)

    def test_fences(self):
        for fence in ['```', '~~~~', '   ```']:
            with self.subTest(fence=fence):
                self.assertEqual(claims_in(fence + '\n' + EXPECTED_POSITIVE[0] + '\n' + fence), [])
        self.assertEqual(claims_in('````\n' + EXPECTED_POSITIVE[0] + '\n```\n' + EXPECTED_POSITIVE[0]), [])

    def test_inline_code_counts(self):
        self.assertEqual(len(claims_in('`financial document extraction`')), 1)

    def test_normalization(self):
        result = claims_in("It doesn't extract-financial-document.\n\nFinancial\n document extraction.")
        self.assertEqual([c['family'] for c in result], ['NOFINANCIALDOCUMENTEXTRACTION', 'FINANCIALDOCUMENTEXTRACTION'])

    def test_longest_and_boundaries(self):
        result = claims_in('Extract financial documents data')
        self.assertEqual([c['phrase'] for c in result], ['extract financial documents data'])
        self.assertEqual(claims_in('preextract financial documentsSuffix'), [])

    def test_docs_selection(self):
        self.write('other.md', EXPECTED_POSITIVE[0])
        self.assertEqual(audit(self.root)['claims'], [])
        self.write('nested/docs/topic.md', EXPECTED_POSITIVE[0])
        self.assertEqual(len(audit(self.root)['claims']), 1)

    def test_split_module(self):
        self.write('README.md', EXPECTED_POSITIVE[0])
        self.write('a.py', 'import mindee\nc = mindee.Client()')
        self.write('b.py', 'import mindee\nc.parse(product.FinancialDocumentV1, source)')
        self.assertEqual(self.run_cli()[0], 2)

    def test_symlinks(self):
        outside = self.root / 'fixtures' / 'outside.py'
        outside.parent.mkdir()
        outside.write_text(GOOD)
        (self.root / 'linked.py').symlink_to(outside)
        (self.root / 'linked_dir').symlink_to(outside.parent, target_is_directory=True)
        self.write('README.md', EXPECTED_POSITIVE[0])
        self.assertEqual(audit(self.root)['evidence'], [])

    def test_ignore_prefix_components(self):
        self.write('README.md', EXPECTED_POSITIVE[0])
        self.write('vendor/main.py', GOOD)
        self.assertEqual(audit(self.root, ['vendor'])['evidence'], [])
        self.write('vendor2/main.py', GOOD)
        self.assertEqual(len(audit(self.root, ['vendor'])['evidence']), 1)
        self.assertEqual(self.run_cli('--ignore', 'vendor', '--ignore', 'vendor2')[0], 2)

    def test_cli_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exc:
            main(['--version'])
        self.assertEqual(exc.exception.code, 0)
        self.assertEqual(out.getvalue().strip(), '0.1.0')

    def test_cli_usage_errors(self):
        for argv in [[], ['bad'], ['audit', '--fail-on', 'HIGH'], ['audit', '--ignore'], ['audit', '.', 'extra']]:
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                main(argv)
            self.assertEqual(exc.exception.code, 1)

    def test_bad_path(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['audit', str(self.root / 'absent')]), 1)

    def test_io_error(self):
        with patch('financial_document_extraction_claim_audit.audit.os.walk', side_effect=PermissionError('unreadable')):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['audit', str(self.root)]), 1)

    def test_verbose(self):
        self.write('README.md', EXPECTED_POSITIVE[0])
        code, text = self.run_cli('--verbose')
        self.assertEqual(code, 2)
        self.assertIn('README.md:1', text)

    def test_module_entrypoint(self):
        result = subprocess.run([sys.executable, '-m', 'financial_document_extraction_claim_audit', '--version'],
                                text=True, capture_output=True, check=True)
        self.assertEqual(result.stdout.strip(), '0.1.0')

    def test_console_entrypoint_metadata(self):
        config = (Path(__file__).resolve().parents[1] / 'pyproject.toml')
        if config.exists():
            self.assertIn('financial-document-extraction-claim-audit = "financial_document_extraction_claim_audit.__main__:main"', config.read_text())
        else:
            from importlib.metadata import distribution
            entries = distribution('financial-document-extraction-claim-audit').entry_points
            self.assertTrue(any(e.name == 'financial-document-extraction-claim-audit' for e in entries))

    def test_readme_self_audit_and_phrase_fencing(self):
        root = Path(__file__).resolve().parents[1]
        if (root / 'README.md').exists():
            self.assertEqual(claims_in((root / 'README.md').read_text()), [])
            self.assertEqual(audit(root)['verdict'], 'PASS')

    def test_not_listed_claims(self):
        for text in ['extract financial statement', 'financial statement extraction', 'extract balance sheet',
                     'balance sheet extraction', 'extract email', 'email extraction', 'extract emails',
                     'extract text from financial document', 'financial document management',
                     'financial document storage', 'financial document archiving', 'financial document automation',
                     'financial document workflow', 'financial documents include invoices, statements, and tax forms']:
            with self.subTest(text=text):
                self.assertEqual(claims_in(text), [])


def evidence_test(source, expected):
    def test(self):
        self.assertEqual(bool(module_evidence(source)), expected, source)
    return test


# Generate separately counted cases with a fixed independent vocabulary oracle.
for index, name in enumerate(EXPECTED_GENERIC):
    setattr(AuditTests, 'test_generic_attribute_%02d' % index, evidence_test('x.' + name + '(source)', True))
    setattr(AuditTests, 'test_generic_from_import_%02d' % index,
            evidence_test('from provider import ' + name + ' as f\nf(source)', True))
    setattr(AuditTests, 'test_generic_bare_%02d' % index, evidence_test(name + '(source)', False))
    setattr(AuditTests, 'test_generic_shadow_%02d' % index,
            evidence_test('def ' + name + '(x): pass\nx.' + name + '(source)', False))

MINDEE_GOOD = [
    GOOD,
    'from mindee import Client\nfrom mindee.product import FinancialDocumentV1\nc = Client()\nc.parse(FinancialDocumentV1, source)',
    'import mindee\nmindee.Client()\nx.parse(mindee.product.FinancialDocumentV1, source)',
    'import mindee\nmindee.Client()\nx.parse(mindee.product.financial_document.FinancialDocumentV1, source)',
    'from mindee import Client as C\nC()\nx.parse(product_class=product.FinancialDocumentV1)',
    'import mindee as md\nmd.Client()\nx.parse(product.FinancialDocumentV1)',
    'import mindee.v1.product as product\nfrom mindee import Client as C\nC()\nx.parse(product.FinancialDocumentV1)',
    'from mindee.product.financial_document import FinancialDocumentV1\nfrom mindee import Client\nClient()\nx.parse(FinancialDocumentV1)',
    'from provider import extract_financial_document as do_it\ndo_it(source)',
    'import provider as p\np.extract_financial_document(source)',
    'import provider.extract_financial_document as f\nf(source)',
]
for index, source in enumerate(MINDEE_GOOD):
    setattr(AuditTests, 'test_alias_and_mindee_%02d' % index, evidence_test(source, True))

OTHER_PRODUCTS = ('InvoiceV4 ReceiptV5 PassportV1 BankCheckV1 BankAccountDetailsV1 BankAccountDetailsV2 '
                  'PayslipV2 PayslipV3 NutritionFactsLabelV1 HealthcareCardV1 BusinessCardV1 CustomV1 GeneratedV1 '
                  'BillOfLadingV1 ResumeV1 DeliveryNoteV1 DriverLicenseV1 IdCardV1 InternationalIdV2 CarteGriseV1 '
                  'EnergyBillV1 MaterialCertificateV1 BarcodeReaderV1 CropperV1 UsMailV2 UsMailV3 '
                  'FinancialDocumentV2 TypeFinancialDocumentV1').split()
for product in OTHER_PRODUCTS:
    setattr(AuditTests, 'test_other_product_' + product,
            evidence_test('import mindee\nc=mindee.Client()\nc.parse(product.' + product + ', source)', False))

AZURE_MODELS = ('invoice receipt layout read idDocument check.us tax.us bankStatement.us payStub.us '
                'healthInsuranceCard.us businessCard creditCard contract mortgage.us.1003 vaccinationCard financialDocument').split()
for index, model in enumerate(AZURE_MODELS):
    setattr(AuditTests, 'test_azure_model_%02d' % index,
            evidence_test('from azure.ai.documentintelligence import DocumentIntelligenceClient\nc=DocumentIntelligenceClient()\nc.begin_analyze_document("prebuilt-' + model + '", source)', False))

VERYFI_METHODS = ('process_any_document process_any_document_url process_document process_document_url '
                 'process_w2_document process_w9_document process_w8_document process_check process_check_url '
                 'process_check_with_remittance process_check_with_remittance_url process_bank_statement_document '
                 'process_bank_statement_document_url process_bussines_card_document process_bussines_card_document_url '
                 'classify_document get_business_cards get_business_card delete_business_card '
                 'process_financial_document process_financial_document_url').split()
for method in VERYFI_METHODS:
    setattr(AuditTests, 'test_veryfi_' + method,
            evidence_test('import veryfi\nc=veryfi.Client()\nc.' + method + '(source)', False))

NOT_EVIDENCE = [
    'import mindee', 'import veryfi', 'import azure.ai.formrecognizer',
    'import azure.ai.documentintelligence', 'import google.cloud.documentai', 'import boto3',
    'import mindee\nc=mindee.Client()', 'x.parse(product.FinancialDocumentV1)',
    'from azure.ai.documentintelligence import DocumentIntelligenceClient\nDocumentIntelligenceClient()',
    'import veryfi\nveryfi.Client()',
    'import requests\nrequests.post("https://api.veryfi.com/api/v8/partner/documents", files=files)',
    'from google.cloud import documentai\nc=documentai.DocumentProcessorServiceClient()\nc.process_document(request=request)',
    'from google.cloud import documentai\nc.batch_process_documents(request=request)',
    'import boto3\nboto3.client("textract").analyze_document(Document=d)',
    'import boto3\nboto3.client("textract").analyze_expense(Document=d)',
    'import boto3\nboto3.client("textract").analyze_id(Document=d)',
    'x.start_document_analysis(Document=d)', 'x.get_expense_analysis(JobId=j)',
    'from llama_parse import LlamaParse\nLlamaParse().load_data(path)',
    'nanonets.predict(model_id="opaque", file=path)', 'docsumo.upload(path)',
    'abbyy.process(skill_id="opaque")', 'rossum.upload(queue="opaque")',
    'klippa.process(template="opaque")', 'parseur.upload(mailbox="opaque")', 'extend.extract(workflow="opaque")',
    'import mindee\nc=mindee.ClientV2()\nc.enqueue_and_get_inference(model_id="opaque")',
    'x.extract_document(source)', 'x.parse_document(source)', 'x.document_extraction(source)',
    'x.extract_financial_statement(source)', 'x.parse_financial_statement(source)', 'x.financial_statement_extraction(source)',
    'x.extract_email(source)', 'x.parse_email(source)', 'x.email_extraction(source)',
    'import pdfplumber\npdfplumber.open(path).pages[0].extract_text()',
    'import fitz\nfitz.open(path)[0].get_text()', 'x.extract_text()',
    'import pytesseract\npytesseract.image_to_string(image)',
    'import pandas\npandas.read_csv(path)', 'pandas.read_excel(path)',
    'import camelot\ncamelot.read_pdf(path)', 'import tabula\ntabula.read_pdf(path)', 'tabula.convert_into(path)',
    'page.extract_table()', 'page.extract_tables()', 'page.find_table()', 'page.find_tables()',
    'import re\ntotal=re.search("total (.*)", text)\nfields={"total":total}',
    'text="total 12"\nfields=text.split()',
    'import subprocess\nsubprocess.run(["mindee", "parse", "financial_document", path])',
    'import subprocess\nsubprocess.run(["veryfi", "process", path])',
    '# x.extract_financial_document(source)\ns="x.parse_financial_document(source)"',
    'x.extract_financial_document', 'def broken(',
    'def extract_financial_document(x): return x\nextract_financial_document(source)',
    'from lib import extract_financial_document as f\nf=None\nf(source)',
    'from lib import extract_financial_document as f\nf: object=None\nf(source)',
    'from lib import extract_financial_document as f\nwith manager() as f:\n f(source)',
    'from lib import extract_financial_document as f\nasync def go():\n async with manager() as f:\n  f(source)',
    'import mindee\nmindee=None\nmindee.Client()\nx.parse(product.FinancialDocumentV1)',
    'from mindee import Client\nclass Client: pass\nClient()\nx.parse(product.FinancialDocumentV1)',
    'from mindee import Client as C\nwith manager() as C: C()\nx.parse(product.FinancialDocumentV1)',
    'import mindee\nmindee.Client()\nFinancialDocumentV1=None\nx.parse(FinancialDocumentV1)',
    'class A:\n def extract_financial_document(self): pass\nx.extract_financial_document(source)',
    'import mindee\ndef Client(): pass\nmindee.Client()\nx.parse(product.FinancialDocumentV1)',
    'from mindee import Client\nfrom mindee.product import FinancialDocumentV1 as FD\nClient()\nx.parse(FD)',
    'import provider as p\nwith manager() as p: p.extract_financial_document(source)',
    'from lib import extract_financial_document as f\n(f, other) = values\nf(source)',
]
for model in ['ocr/financial_parser/affinda', 'ocr/invoice_parser/affinda', 'ocr/resume_parser/affinda']:
    NOT_EVIDENCE.append('import requests\nrequests.post("https://api.edenai.run/v3/universal-ai", json={"model":' + repr(model) + ', "input":data})')
for index, source in enumerate(NOT_EVIDENCE):
    setattr(AuditTests, 'test_not_evidence_%02d' % index, evidence_test(source, False))

for index, name in enumerate(['tests/helper.py', 'test_feature.py', 'feature_test.py', 'nested/tests/helper.py']):
    def test(self, name=name):
        self.write('README.md', EXPECTED_POSITIVE[0])
        self.write(name, GOOD)
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'MEDIUM')
    setattr(AuditTests, 'test_test_exclusion_%02d' % index, test)
for folder in ['fixtures', 'docs', 'examples']:
    def test(self, folder=folder):
        self.write('README.md', EXPECTED_POSITIVE[0])
        self.write('nested/' + folder + '/helper.py', GOOD)
        self.assertEqual(audit(self.root)['evidence'], [])
    setattr(AuditTests, 'test_production_exclusion_' + folder, test)
for index, phrase in enumerate(EXPECTED_POSITIVE):
    def test(self, phrase=phrase):
        result = claims_in(phrase)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['phrase'], phrase)
        self.assertEqual(result[0]['family'], 'FINANCIALDOCUMENTEXTRACTION')
    setattr(AuditTests, 'test_positive_phrase_%02d' % index, test)
for index, phrase in enumerate(EXPECTED_NEGATIVE):
    def test(self, phrase=phrase):
        result = claims_in(phrase)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['phrase'], phrase)
        self.assertEqual(result[0]['family'], 'NOFINANCIALDOCUMENTEXTRACTION')
    setattr(AuditTests, 'test_negative_phrase_%02d' % index, test)


if __name__ == '__main__':
    unittest.main()
