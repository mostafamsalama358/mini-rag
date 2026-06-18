import unittest

from utils.text_cleaning import clean_extracted_text
from utils.chunk_metadata import format_source_label, normalize_chunk_metadata


class TextCleaningTests(unittest.TestCase):
    def test_merges_broken_lines(self):
        text = "وحكومة جمهورية\nالسودان"
        self.assertEqual(clean_extracted_text(text), "وحكومة جمهورية السودان")

    def test_removes_standalone_page_numbers(self):
        text = "الفصل الأول\n18\nالمادة (1)"
        self.assertNotIn("\n18\n", clean_extracted_text(text))
        self.assertIn("المادة (1)", clean_extracted_text(text))

    def test_collapses_extra_whitespace(self):
        text = "نص    فيه   مسافات"
        self.assertEqual(clean_extracted_text(text), "نص فيه مسافات")

    def test_fixes_broken_arabic_word_spaces(self):
        text = "جمهورية م صر العربية"
        self.assertEqual(clean_extracted_text(text), "جمهورية مصر العربية")


class ChunkMetadataTests(unittest.TestCase):
    def test_format_source_label_full_metadata(self):
        label = format_source_label(
            {"file_name": "agreement.pdf", "page": 3},
            lang="ar",
        )
        self.assertEqual(label, "agreement.pdf — صفحة 3")

    def test_format_source_label_file_only(self):
        label = format_source_label({"file_name": "notes.txt"}, lang="en")
        self.assertEqual(label, "notes.txt")

    def test_format_source_label_missing_metadata(self):
        self.assertEqual(format_source_label(None, lang="en"), "unknown source")

    def test_normalize_chunk_metadata_drops_none_values(self):
        self.assertEqual(
            normalize_chunk_metadata({"file_name": "a.pdf", "page": None}),
            {"file_name": "a.pdf"},
        )


if __name__ == "__main__":
    unittest.main()
