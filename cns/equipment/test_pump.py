import unittest
import pump

class testPumpInterface(unittest.TestCase):

    def setUp(self):
        self.pump = pump.PumpInterface()

    def testResponseParser(self):
        responses = {
                '\x0200A?S\x03'     : ('00', 'A?', 'S'),
                '\x0200P0.21MM\x03' : ('00', 'P', '0.21MM'),
                '\x0200S\x03'       : ('00', 'S', ''),
                '\x0200P?\x03'      : ('00', 'P', '?'),
                '\x0200P?COM\x03'   : ('00', 'P', '?COM'),
                '\x0200IWDR\x03'    : ('00', 'I', 'WDR'),
                }

        for k, v in responses.items():
            match = self.pump._basic_response.match(k)
            self.assertTrue(match is not None)
            self.assertEqual(match.groups(), v)

if __name__ == '__main__':
    unittest.main()
