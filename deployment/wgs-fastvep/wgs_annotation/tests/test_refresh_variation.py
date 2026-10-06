import csv
import gzip
import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from test_adapter import fixture, adapter, build_chromosome

script = Path(__file__).resolve().parents[1] / 'validation/refresh_variation_annotations.py'
spec = importlib.util.spec_from_file_location('refresh', script)
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def rows(path):
    with gzip.open(path, 'rt') as handle:
        return list(csv.DictReader((line for line in handle if not line.startswith('##')), delimiter='\t'))


class RefreshTests(unittest.TestCase):
    def test_refresh_retains_core_and_plugin_fields_and_audits_frequency_gain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args, _ = fixture(root)
            adapter.run(args)
            original = rows(args.output)
            original[0]['gnomADg_AF'] = '-'
            with gzip.open(args.output, 'wt') as out:
                writer = csv.DictWriter(out, fieldnames=original[0], delimiter='\t')
                writer.writeheader()
                writer.writerows(original)
            old_summary = json.loads(Path(args.summary).read_text())
            old_summary['nonmissing_rows']['gnomADg_AF'] = 0
            Path(args.summary).write_text(json.dumps(old_summary))
            build_chromosome(args.variation_cache, root/'reference.fa', root/'index', '1')
            request = Namespace(input=args.output, input_summary=args.summary, output=str(root/'new.tsv.gz'),
                                summary=str(root/'new.json'), variation_cache=args.variation_cache,
                                reference=str(root/'reference.fa'), variation_index=str(root/'index'))
            result = refresh.refresh(request)
            actual = rows(request.output)
            self.assertEqual(actual[0]['gnomADg_AF'], '0.002')
            for field in original[0]:
                if field not in refresh.CACHE_FIELDS:
                    self.assertEqual(original[0][field], actual[0][field], field)
            self.assertEqual(result['cache_refresh_audit']['gnomADg_AF']['gained'], 1)
            self.assertEqual(result['nonmissing_rows']['gnomADg_AF'], 1)
            self.assertEqual(result['counts'], old_summary['counts'])
            old_summary['counts']['variants'] = 2
            Path(args.summary).write_text(json.dumps(old_summary))
            request.output = str(root/'invalid.tsv.gz')
            with self.assertRaisesRegex(AssertionError, 'counts changed'):
                refresh.refresh(request)
            self.assertFalse(Path(request.output).exists())


if __name__ == '__main__':
    unittest.main()
