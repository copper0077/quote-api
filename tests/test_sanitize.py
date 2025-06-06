import re
import unittest

class FilenameSanitizeTest(unittest.TestCase):
    def test_sanitization(self):
        customer = 'ACME/Corp\nTest '
        safe_customer = re.sub(r'[^A-Za-z0-9_-]+', '_', customer).strip('_')
        filename = f"{safe_customer}_12345.pdf"
        self.assertEqual(filename, 'ACME_Corp_Test_12345.pdf')
        self.assertNotRegex(filename, r'[^A-Za-z0-9_.-]')
        self.assertNotIn('\n', filename)

if __name__ == '__main__':
    unittest.main()
