import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('compare', Path(__file__).parents[1] / 'validation' / 'compare_annotations.py')
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)


class ComparisonTests(unittest.TestCase):
    def test_indel_anchors_do_not_create_missing_variants(self):
        self.assertEqual(compare.variant_key({'#Uploaded_variation': 'chr1_100_A/AT'}),
                         compare.variant_key({'Uploaded_variation': '1_101_-/T'}))
        self.assertEqual(compare.variant_key({'#Uploaded_variation': 'chrX_100_TAC/T'}),
                         compare.variant_key({'#Uploaded_variation': 'X_101_AC/-'}))

    def test_consequence_order_and_af_rounding(self):
        self.assertTrue(compare.equivalent('Consequence', 'missense_variant&splice_region_variant',
                                          'splice_region_variant,missense_variant'))
        self.assertTrue(compare.equivalent('gnomADg_AF', '0.002', '0.0020000001'))
        self.assertFalse(compare.equivalent('gnomADg_AF', '0', '-'))

    def test_hgvs_versions_are_reported_separately(self):
        self.assertTrue(compare.hgvs_reference_version_only('ENSP00000274813.3:p.Arg403Gly',
                                                           'ENSP00000274813.1:p.Arg403Gly'))
        self.assertFalse(compare.hgvs_reference_version_only('ENSP00000274813.3:p.Arg403Gly',
                                                            'ENSP00000274813.1:p.Arg403Ala'))

    def test_alignment_recovers_after_missing_and_extra_records(self):
        key = lambda n: ('1', n, 'A', 'T')
        a = [(key(n), [n]) for n in range(1, 301) if n not in (15, 16)]
        b = [(key(n), [n]) for n in range(1, 301) if n not in (4, 5, 250)]
        rows = list(compare.align(a, b))
        self.assertEqual(sum(bool(old and new) for _, old, new in rows), 295)
        self.assertEqual([k[1] for k, old, new in rows if old and not new], [4, 5, 250])
        self.assertEqual([k[1] for k, old, new in rows if new and not old], [15, 16])

    def test_alignment_handles_local_reordering(self):
        key = lambda n: ('1', n, 'A', 'T')
        rows = list(compare.align([(key(1), [1]), (key(2), [2])],
                                  [(key(2), [2]), (key(1), [1])]))
        self.assertTrue(all(old == new for _, old, new in rows))


if __name__ == '__main__':
    unittest.main()
