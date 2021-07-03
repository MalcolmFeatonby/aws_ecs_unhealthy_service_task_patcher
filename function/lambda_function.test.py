import unittest
import importlib
import logging
import jsonpickle
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('function_test')
logger.setLevel(logging.DEBUG)

#function = importlib.import_module(lambda_function)

function = __import__('lambda_function')
handler = function.lambda_handler

class TestFunction(unittest.TestCase):

  def test_function(self):

    logger.warning('## Calling function under test.')
    context = {'requestid' : '1234'}
    result = handler(None, context)
    print(str(result))
    self.assertRegex(str(result), 'Success', 'Should match')

    logger.warning('## Test run complete.')

if __name__ == '__main__':
    unittest.main()
