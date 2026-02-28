"""
Unit tests for PillBuddy Alexa Handler Lambda Function
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Mock boto3 before importing lambda_function
sys.modules['boto3'] = MagicMock()

# Set up required environment variables
os.environ['DEVICES_TABLE'] = 'test_devices_table'
os.environ['PRESCRIPTIONS_TABLE'] = 'test_prescriptions_table'
os.environ['IOT_ENDPOINT'] = 'test_iot_endpoint'

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_function import supports_apl, fetch_device_slots, build_apl_datasources


class TestSupportsAPL(unittest.TestCase):
    """Test cases for supports_apl() function"""
    
    def test_supports_apl_with_apl_interface(self):
        """Test that supports_apl returns True when APL interface is present"""
        event = {
            'context': {
                'System': {
                    'device': {
                        'supportedInterfaces': {
                            'Alexa.Presentation.APL': {}
                        }
                    }
                }
            }
        }
        self.assertTrue(supports_apl(event))
    
    def test_supports_apl_without_apl_interface(self):
        """Test that supports_apl returns False when APL interface is not present"""
        event = {
            'context': {
                'System': {
                    'device': {
                        'supportedInterfaces': {
                            'AudioPlayer': {}
                        }
                    }
                }
            }
        }
        self.assertFalse(supports_apl(event))
    
    def test_supports_apl_with_empty_interfaces(self):
        """Test that supports_apl returns False when supportedInterfaces is empty"""
        event = {
            'context': {
                'System': {
                    'device': {
                        'supportedInterfaces': {}
                    }
                }
            }
        }
        self.assertFalse(supports_apl(event))
    
    def test_supports_apl_missing_context(self):
        """Test that supports_apl returns False when context is missing"""
        event = {}
        self.assertFalse(supports_apl(event))
    
    def test_supports_apl_missing_system(self):
        """Test that supports_apl returns False when System is missing"""
        event = {
            'context': {}
        }
        self.assertFalse(supports_apl(event))
    
    def test_supports_apl_missing_device(self):
        """Test that supports_apl returns False when device is missing"""
        event = {
            'context': {
                'System': {}
            }
        }
        self.assertFalse(supports_apl(event))
    
    def test_supports_apl_missing_supported_interfaces(self):
        """Test that supports_apl returns False when supportedInterfaces is missing"""
        event = {
            'context': {
                'System': {
                    'device': {}
                }
            }
        }
        self.assertFalse(supports_apl(event))
    
    def test_supports_apl_with_none_value(self):
        """Test that supports_apl returns False when supportedInterfaces is None"""
        event = {
            'context': {
                'System': {
                    'device': {
                        'supportedInterfaces': None
                    }
                }
            }
        }
        self.assertFalse(supports_apl(event))
    
    def test_supports_apl_with_multiple_interfaces(self):
        """Test that supports_apl returns True when APL is among multiple interfaces"""
        event = {
            'context': {
                'System': {
                    'device': {
                        'supportedInterfaces': {
                            'AudioPlayer': {},
                            'Alexa.Presentation.APL': {},
                            'Display': {}
                        }
                    }
                }
            }
        }
        self.assertTrue(supports_apl(event))


class TestFetchDeviceSlots(unittest.TestCase):
    """Test cases for fetch_device_slots() function"""
    
    @patch('lambda_function.devices_table')
    def test_fetch_device_slots_success(self, mock_table):
        """Test that fetch_device_slots returns slot data when device exists"""
        mock_table.get_item.return_value = {
            'Item': {
                'device_id': 'esp32_001',
                'slots': {
                    '1': {'in_holder': True, 'last_state_change': 1700000000000},
                    '2': {'in_holder': False, 'last_state_change': 1699999000000},
                    '3': {'in_holder': True, 'last_state_change': 1699998000000}
                }
            }
        }
        
        result = fetch_device_slots('esp32_001')
        
        self.assertEqual(len(result), 3)
        self.assertTrue(result['1']['in_holder'])
        self.assertFalse(result['2']['in_holder'])
        self.assertTrue(result['3']['in_holder'])
        mock_table.get_item.assert_called_once_with(Key={'device_id': 'esp32_001'})
    
    @patch('lambda_function.devices_table')
    def test_fetch_device_slots_device_not_found(self, mock_table):
        """Test that fetch_device_slots returns empty dict when device not found"""
        mock_table.get_item.return_value = {}
        
        result = fetch_device_slots('nonexistent_device')
        
        self.assertEqual(result, {})
        mock_table.get_item.assert_called_once_with(Key={'device_id': 'nonexistent_device'})
    
    @patch('lambda_function.devices_table')
    def test_fetch_device_slots_no_slots_data(self, mock_table):
        """Test that fetch_device_slots returns empty dict when slots data is missing"""
        mock_table.get_item.return_value = {
            'Item': {
                'device_id': 'esp32_001',
                'online': True
            }
        }
        
        result = fetch_device_slots('esp32_001')
        
        self.assertEqual(result, {})
    
    @patch('lambda_function.devices_table')
    def test_fetch_device_slots_dynamodb_error(self, mock_table):
        """Test that fetch_device_slots returns empty dict on DynamoDB error"""
        mock_table.get_item.side_effect = Exception('DynamoDB error')
        
        result = fetch_device_slots('esp32_001')
        
        self.assertEqual(result, {})
    
    @patch('lambda_function.devices_table')
    def test_fetch_device_slots_all_slots_empty(self, mock_table):
        """Test that fetch_device_slots handles all slots being empty"""
        mock_table.get_item.return_value = {
            'Item': {
                'device_id': 'esp32_001',
                'slots': {
                    '1': {'in_holder': False, 'last_state_change': 1700000000000},
                    '2': {'in_holder': False, 'last_state_change': 1699999000000},
                    '3': {'in_holder': False, 'last_state_change': 1699998000000}
                }
            }
        }
        
        result = fetch_device_slots('esp32_001')
        
        self.assertEqual(len(result), 3)
        self.assertFalse(result['1']['in_holder'])
        self.assertFalse(result['2']['in_holder'])
        self.assertFalse(result['3']['in_holder'])
    
    @patch('lambda_function.devices_table')
    def test_fetch_device_slots_all_slots_filled(self, mock_table):
        """Test that fetch_device_slots handles all slots being filled"""
        mock_table.get_item.return_value = {
            'Item': {
                'device_id': 'esp32_001',
                'slots': {
                    '1': {'in_holder': True, 'last_state_change': 1700000000000},
                    '2': {'in_holder': True, 'last_state_change': 1699999000000},
                    '3': {'in_holder': True, 'last_state_change': 1699998000000}
                }
            }
        }
        
        result = fetch_device_slots('esp32_001')
        
        self.assertEqual(len(result), 3)
        self.assertTrue(result['1']['in_holder'])
        self.assertTrue(result['2']['in_holder'])
        self.assertTrue(result['3']['in_holder'])


class TestBuildAPLDatasources(unittest.TestCase):
    """Test cases for build_apl_datasources() function"""
    
    def test_build_apl_datasources_all_slots_filled(self):
        """Test datasources with all three slots filled and in holder"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 30, 'in_holder': True},
            '2': {'slot_number': 2, 'prescription_name': 'Ibuprofen', 'pill_count': 15, 'in_holder': True},
            '3': {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 60, 'in_holder': True}
        }
        
        result = build_apl_datasources(combined_slots)
        
        self.assertIn('slots', result)
        self.assertEqual(len(result['slots']), 3)
        
        # Check slot 1
        self.assertEqual(result['slots'][0]['slot_number'], 1)
        self.assertEqual(result['slots'][0]['prescription_name'], 'Aspirin')
        self.assertEqual(result['slots'][0]['pill_count'], 30)
        self.assertTrue(result['slots'][0]['in_holder'])
        self.assertFalse(result['slots'][0]['low_pill_warning'])
        
        # Check slot 2
        self.assertEqual(result['slots'][1]['slot_number'], 2)
        self.assertEqual(result['slots'][1]['prescription_name'], 'Ibuprofen')
        self.assertEqual(result['slots'][1]['pill_count'], 15)
        self.assertTrue(result['slots'][1]['in_holder'])
        self.assertFalse(result['slots'][1]['low_pill_warning'])
    
    def test_build_apl_datasources_low_pill_warning(self):
        """Test that low_pill_warning is True when pill_count <= 7"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 7, 'in_holder': True},
            '2': {'slot_number': 2, 'prescription_name': 'Ibuprofen', 'pill_count': 5, 'in_holder': True},
            '3': {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 1, 'in_holder': True}
        }
        
        result = build_apl_datasources(combined_slots)
        
        # All slots should have low_pill_warning = True
        self.assertTrue(result['slots'][0]['low_pill_warning'])
        self.assertTrue(result['slots'][1]['low_pill_warning'])
        self.assertTrue(result['slots'][2]['low_pill_warning'])
    
    def test_build_apl_datasources_no_low_pill_warning_above_threshold(self):
        """Test that low_pill_warning is False when pill_count > 7"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 8, 'in_holder': True},
            '2': {'slot_number': 2, 'prescription_name': 'Ibuprofen', 'pill_count': 20, 'in_holder': True},
            '3': {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 100, 'in_holder': True}
        }
        
        result = build_apl_datasources(combined_slots)
        
        # All slots should have low_pill_warning = False
        self.assertFalse(result['slots'][0]['low_pill_warning'])
        self.assertFalse(result['slots'][1]['low_pill_warning'])
        self.assertFalse(result['slots'][2]['low_pill_warning'])
    
    def test_build_apl_datasources_empty_slots(self):
        """Test datasources with empty slots (not in holder)"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': None, 'pill_count': 0, 'in_holder': False},
            '2': {'slot_number': 2, 'prescription_name': None, 'pill_count': 0, 'in_holder': False},
            '3': {'slot_number': 3, 'prescription_name': None, 'pill_count': 0, 'in_holder': False}
        }
        
        result = build_apl_datasources(combined_slots)
        
        self.assertEqual(len(result['slots']), 3)
        
        for i in range(3):
            self.assertEqual(result['slots'][i]['slot_number'], i + 1)
            self.assertEqual(result['slots'][i]['prescription_name'], 'Empty Slot')
            self.assertEqual(result['slots'][i]['pill_count'], 0)
            self.assertFalse(result['slots'][i]['in_holder'])
            self.assertFalse(result['slots'][i]['low_pill_warning'])
    
    def test_build_apl_datasources_mixed_slots(self):
        """Test datasources with mix of filled and empty slots"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 5, 'in_holder': True},
            '2': {'slot_number': 2, 'prescription_name': None, 'pill_count': 0, 'in_holder': False},
            '3': {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 30, 'in_holder': True}
        }
        
        result = build_apl_datasources(combined_slots)
        
        # Slot 1: filled with low pill warning
        self.assertEqual(result['slots'][0]['prescription_name'], 'Aspirin')
        self.assertTrue(result['slots'][0]['in_holder'])
        self.assertTrue(result['slots'][0]['low_pill_warning'])
        
        # Slot 2: empty
        self.assertEqual(result['slots'][1]['prescription_name'], 'Empty Slot')
        self.assertFalse(result['slots'][1]['in_holder'])
        self.assertFalse(result['slots'][1]['low_pill_warning'])
        
        # Slot 3: filled without low pill warning
        self.assertEqual(result['slots'][2]['prescription_name'], 'Vitamin D')
        self.assertTrue(result['slots'][2]['in_holder'])
        self.assertFalse(result['slots'][2]['low_pill_warning'])
    
    def test_build_apl_datasources_no_warning_when_not_in_holder(self):
        """Test that low_pill_warning is False when bottle is not in holder, even with low count"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 3, 'in_holder': False},
            '2': {'slot_number': 2, 'prescription_name': 'Ibuprofen', 'pill_count': 5, 'in_holder': False},
            '3': {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 1, 'in_holder': False}
        }
        
        result = build_apl_datasources(combined_slots)
        
        # All slots should have low_pill_warning = False because not in holder
        self.assertFalse(result['slots'][0]['low_pill_warning'])
        self.assertFalse(result['slots'][1]['low_pill_warning'])
        self.assertFalse(result['slots'][2]['low_pill_warning'])
    
    def test_build_apl_datasources_missing_slot_data(self):
        """Test datasources with missing slot data (uses defaults)"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 10, 'in_holder': True}
            # Slots 2 and 3 are missing
        }
        
        result = build_apl_datasources(combined_slots)
        
        self.assertEqual(len(result['slots']), 3)
        
        # Slot 1: has data
        self.assertEqual(result['slots'][0]['prescription_name'], 'Aspirin')
        self.assertTrue(result['slots'][0]['in_holder'])
        
        # Slots 2 and 3: use defaults
        self.assertEqual(result['slots'][1]['prescription_name'], 'Empty Slot')
        self.assertFalse(result['slots'][1]['in_holder'])
        self.assertEqual(result['slots'][2]['prescription_name'], 'Empty Slot')
        self.assertFalse(result['slots'][2]['in_holder'])
    
    def test_build_apl_datasources_zero_pills_no_warning(self):
        """Test that low_pill_warning is False when pill_count is 0"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 0, 'in_holder': True},
            '2': {'slot_number': 2, 'prescription_name': 'Ibuprofen', 'pill_count': 0, 'in_holder': True},
            '3': {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 0, 'in_holder': True}
        }
        
        result = build_apl_datasources(combined_slots)
        
        # All slots should have low_pill_warning = False (0 pills means empty, not low)
        self.assertFalse(result['slots'][0]['low_pill_warning'])
        self.assertFalse(result['slots'][1]['low_pill_warning'])
        self.assertFalse(result['slots'][2]['low_pill_warning'])
    
    def test_build_apl_datasources_boundary_threshold(self):
        """Test low_pill_warning at boundary values (7 and 8 pills)"""
        combined_slots = {
            '1': {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 7, 'in_holder': True},
            '2': {'slot_number': 2, 'prescription_name': 'Ibuprofen', 'pill_count': 8, 'in_holder': True},
            '3': {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 6, 'in_holder': True}
        }
        
        result = build_apl_datasources(combined_slots)
        
        # 7 pills: warning should be True
        self.assertTrue(result['slots'][0]['low_pill_warning'])
        # 8 pills: warning should be False
        self.assertFalse(result['slots'][1]['low_pill_warning'])
        # 6 pills: warning should be True
        self.assertTrue(result['slots'][2]['low_pill_warning'])


class TestLoadAPLDocument(unittest.TestCase):
    """Test cases for load_apl_document() function"""
    
    @patch('lambda_function.open', create=True)
    @patch('lambda_function.os.path.dirname')
    @patch('lambda_function.os.path.abspath')
    @patch('lambda_function.os.path.join')
    def test_load_apl_document_success(self, mock_join, mock_abspath, mock_dirname, mock_open):
        """Test that load_apl_document successfully loads and parses APL template"""
        from lambda_function import load_apl_document
        
        # Mock file path construction
        mock_abspath.return_value = '/lambda/lambda_function.py'
        mock_dirname.return_value = '/lambda'
        mock_join.return_value = '/lambda/apl_templates/pill_status_display.json'
        
        # Mock file content
        mock_file_content = '{"type": "APL", "version": "1.6", "mainTemplate": {}}'
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = mock_file_content
        mock_open.return_value = mock_file
        
        # Mock json.load to return parsed content
        with patch('lambda_function.json.load') as mock_json_load:
            mock_json_load.return_value = {"type": "APL", "version": "1.6", "mainTemplate": {}}
            
            result = load_apl_document()
            
            self.assertIsNotNone(result)
            self.assertEqual(result['type'], 'APL')
            self.assertEqual(result['version'], '1.6')
            self.assertIn('mainTemplate', result)
    
    @patch('lambda_function.open', create=True)
    @patch('lambda_function.os.path.dirname')
    @patch('lambda_function.os.path.abspath')
    @patch('lambda_function.os.path.join')
    def test_load_apl_document_file_not_found(self, mock_join, mock_abspath, mock_dirname, mock_open):
        """Test that load_apl_document returns None when file is not found"""
        from lambda_function import load_apl_document
        
        # Mock file path construction
        mock_abspath.return_value = '/lambda/lambda_function.py'
        mock_dirname.return_value = '/lambda'
        mock_join.return_value = '/lambda/apl_templates/pill_status_display.json'
        
        # Mock FileNotFoundError
        mock_open.side_effect = FileNotFoundError('File not found')
        
        result = load_apl_document()
        
        self.assertIsNone(result)
    
    @patch('lambda_function.open', create=True)
    @patch('lambda_function.os.path.dirname')
    @patch('lambda_function.os.path.abspath')
    @patch('lambda_function.os.path.join')
    def test_load_apl_document_json_decode_error(self, mock_join, mock_abspath, mock_dirname, mock_open):
        """Test that load_apl_document returns None when JSON is invalid"""
        from lambda_function import load_apl_document
        
        # Mock file path construction
        mock_abspath.return_value = '/lambda/lambda_function.py'
        mock_dirname.return_value = '/lambda'
        mock_join.return_value = '/lambda/apl_templates/pill_status_display.json'
        
        # Mock file with invalid JSON
        mock_file = MagicMock()
        mock_open.return_value = mock_file
        
        # Mock json.load to raise JSONDecodeError
        with patch('lambda_function.json.load') as mock_json_load:
            mock_json_load.side_effect = json.JSONDecodeError('Invalid JSON', '', 0)
            
            result = load_apl_document()
            
            self.assertIsNone(result)
    
    @patch('lambda_function.open', create=True)
    @patch('lambda_function.os.path.dirname')
    @patch('lambda_function.os.path.abspath')
    @patch('lambda_function.os.path.join')
    def test_load_apl_document_generic_exception(self, mock_join, mock_abspath, mock_dirname, mock_open):
        """Test that load_apl_document returns None on generic exception"""
        from lambda_function import load_apl_document
        
        # Mock file path construction
        mock_abspath.return_value = '/lambda/lambda_function.py'
        mock_dirname.return_value = '/lambda'
        mock_join.return_value = '/lambda/apl_templates/pill_status_display.json'
        
        # Mock generic exception
        mock_open.side_effect = Exception('Unexpected error')
        
        result = load_apl_document()
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()



class TestBuildResponse(unittest.TestCase):
    """Test cases for build_response() function"""
    
    def test_build_response_basic(self):
        """Test basic response without APL"""
        from lambda_function import build_response
        
        result = build_response('Hello world')
        
        self.assertEqual(result['version'], '1.0')
        self.assertEqual(result['response']['outputSpeech']['type'], 'PlainText')
        self.assertEqual(result['response']['outputSpeech']['text'], 'Hello world')
        self.assertFalse(result['response']['shouldEndSession'])
        self.assertEqual(result['sessionAttributes'], {})
        self.assertNotIn('directives', result['response'])
    
    def test_build_response_with_session_attributes(self):
        """Test response with session attributes"""
        from lambda_function import build_response
        
        session_attrs = {'user_id': '123', 'state': 'active'}
        result = build_response('Hello', session_attributes=session_attrs)
        
        self.assertEqual(result['sessionAttributes'], session_attrs)
    
    def test_build_response_with_should_end_session(self):
        """Test response with shouldEndSession set to True"""
        from lambda_function import build_response
        
        result = build_response('Goodbye', should_end_session=True)
        
        self.assertTrue(result['response']['shouldEndSession'])
    
    def test_build_response_with_reprompt(self):
        """Test response with reprompt text"""
        from lambda_function import build_response
        
        result = build_response('What would you like?', reprompt_text='Please say something')
        
        self.assertIn('reprompt', result['response'])
        self.assertEqual(result['response']['reprompt']['outputSpeech']['type'], 'PlainText')
        self.assertEqual(result['response']['reprompt']['outputSpeech']['text'], 'Please say something')
    
    def test_build_response_with_apl_directive(self):
        """Test response with APL directive when document and datasources provided"""
        from lambda_function import build_response
        
        apl_doc = {'type': 'APL', 'version': '1.6', 'mainTemplate': {}}
        apl_data = {'slots': [{'slot_number': 1, 'prescription_name': 'Aspirin'}]}
        
        result = build_response('Here is your status', apl_document=apl_doc, apl_datasources=apl_data)
        
        self.assertIn('directives', result['response'])
        self.assertEqual(len(result['response']['directives']), 1)
        
        directive = result['response']['directives'][0]
        self.assertEqual(directive['type'], 'Alexa.Presentation.APL.RenderDocument')
        self.assertEqual(directive['token'], 'pillStatusToken')
        self.assertEqual(directive['document'], apl_doc)
        self.assertEqual(directive['datasources'], apl_data)
    
    def test_build_response_with_apl_maintains_speech(self):
        """Test that APL directive doesn't affect outputSpeech"""
        from lambda_function import build_response
        
        apl_doc = {'type': 'APL', 'version': '1.6'}
        apl_data = {'slots': []}
        
        result = build_response('Status message', apl_document=apl_doc, apl_datasources=apl_data)
        
        self.assertEqual(result['response']['outputSpeech']['text'], 'Status message')
        self.assertIn('directives', result['response'])
    
    def test_build_response_with_apl_maintains_should_end_session(self):
        """Test that APL directive doesn't affect shouldEndSession"""
        from lambda_function import build_response
        
        apl_doc = {'type': 'APL', 'version': '1.6'}
        apl_data = {'slots': []}
        
        result = build_response('Status', should_end_session=True, apl_document=apl_doc, apl_datasources=apl_data)
        
        self.assertTrue(result['response']['shouldEndSession'])
        self.assertIn('directives', result['response'])
    
    def test_build_response_without_apl_document_only(self):
        """Test that no directive is added when only apl_document is provided"""
        from lambda_function import build_response
        
        apl_doc = {'type': 'APL', 'version': '1.6'}
        
        result = build_response('Hello', apl_document=apl_doc)
        
        self.assertNotIn('directives', result['response'])
    
    def test_build_response_without_apl_datasources_only(self):
        """Test that no directive is added when only apl_datasources is provided"""
        from lambda_function import build_response
        
        apl_data = {'slots': []}
        
        result = build_response('Hello', apl_datasources=apl_data)
        
        self.assertNotIn('directives', result['response'])
    
    def test_build_response_with_all_parameters(self):
        """Test response with all parameters including APL"""
        from lambda_function import build_response
        
        apl_doc = {'type': 'APL', 'version': '1.6'}
        apl_data = {'slots': [{'slot_number': 1}]}
        session_attrs = {'user': 'test'}
        
        result = build_response(
            'Complete response',
            session_attributes=session_attrs,
            should_end_session=True,
            reprompt_text='Reprompt',
            apl_document=apl_doc,
            apl_datasources=apl_data
        )
        
        # Verify all components are present
        self.assertEqual(result['response']['outputSpeech']['text'], 'Complete response')
        self.assertEqual(result['sessionAttributes'], session_attrs)
        self.assertTrue(result['response']['shouldEndSession'])
        self.assertIn('reprompt', result['response'])
        self.assertIn('directives', result['response'])
        self.assertEqual(result['response']['directives'][0]['type'], 'Alexa.Presentation.APL.RenderDocument')
    
    def test_build_response_apl_directive_structure(self):
        """Test that APL directive has correct structure with all required fields"""
        from lambda_function import build_response
        
        apl_doc = {
            'type': 'APL',
            'version': '1.6',
            'mainTemplate': {
                'items': []
            }
        }
        apl_data = {
            'slots': [
                {'slot_number': 1, 'prescription_name': 'Aspirin', 'pill_count': 30, 'in_holder': True, 'low_pill_warning': False},
                {'slot_number': 2, 'prescription_name': 'Empty Slot', 'pill_count': 0, 'in_holder': False, 'low_pill_warning': False},
                {'slot_number': 3, 'prescription_name': 'Vitamin D', 'pill_count': 5, 'in_holder': True, 'low_pill_warning': True}
            ]
        }
        
        result = build_response('Your pill status', apl_document=apl_doc, apl_datasources=apl_data)
        
        directive = result['response']['directives'][0]
        
        # Verify all required fields are present
        self.assertIn('type', directive)
        self.assertIn('token', directive)
        self.assertIn('document', directive)
        self.assertIn('datasources', directive)
        
        # Verify field values
        self.assertEqual(directive['type'], 'Alexa.Presentation.APL.RenderDocument')
        self.assertEqual(directive['token'], 'pillStatusToken')
        self.assertEqual(directive['document'], apl_doc)
        self.assertEqual(directive['datasources'], apl_data)
        self.assertEqual(len(directive['datasources']['slots']), 3)
