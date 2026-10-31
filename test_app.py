import unittest
from app import app, init_db

class CampusFindTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        # Initialize the test database
        init_db()

    def test_future_item_date_regression(self):
        # Attempt to report an item with a date far in the future (Year 2050)
        response = self.app.post('/report', data={
            'title': 'Time Traveler Watch',
            'category': 'Electronics',
            'item_status': 'Lost',
            'description': 'Lost in the future.',
            'location': 'Science Building',
            'item_date': '2050-01-01',  # Future date
            'contact_name': 'Marty McFly',
            'contact_email': 'marty@example.com'
        })
        
        # The test passes if the server correctly returns the error message
        self.assertIn(b'The item date cannot be in the future.', response.data)

if __name__ == '__main__':
    unittest.main()