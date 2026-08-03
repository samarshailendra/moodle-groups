import tempfile
import unittest
from pathlib import Path

from UnitsAndGroups import CsvFormatError, load_group_memberships


class LoadGroupMembershipsTests(unittest.TestCase):
    def load_csv(self, contents: str):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "groups.csv"
            path.write_text(contents, encoding="utf-8")
            return load_group_memberships(path)

    def test_loads_multiple_student_ids_on_one_row(self):
        groups = self.load_csv("Group A,S100,S101\nGroup B,S102\n")

        self.assertEqual(groups, {"Group A": ["S100", "S101"], "Group B": ["S102"]})

    def test_loads_repeated_group_rows_with_optional_header(self):
        groups = self.load_csv("GroupName,StudentId\nGroup A,S100\nGroup A,S101\n")

        self.assertEqual(groups, {"Group A": ["S100", "S101"]})

    def test_rejects_rows_without_a_student_id(self):
        with self.assertRaisesRegex(CsvFormatError, "Line 1"):
            self.load_csv("Group A\n")


if __name__ == "__main__":
    unittest.main()
