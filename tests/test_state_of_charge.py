import unittest

from victron_mk3 import Handler, StateOfChargeResponse, _VictronMK3Driver


class RecordingHandler(Handler):
    def __init__(self) -> None:
        self.responses = []

    def on_response(self, response) -> None:
        self.responses.append(response)


class StateOfChargeTests(unittest.TestCase):
    def test_supported_state_of_charge_is_scaled_and_delivered(self) -> None:
        driver = _VictronMK3Driver()
        driver._variable_id_queue = [13]
        handler = RecordingHandler()

        # RAM variable 13 reports scale 1 and offset 0.
        driver._handle_variable_info_response(
            handler,
            bytes([0xFF, ord("X"), 0x8E, 1, 0, 0x8F, 0, 0]),
        )
        driver._handle_state_of_charge_response(
            handler,
            bytes([0xFF, ord("Y"), 0x85, 73, 0]),
        )

        self.assertEqual(len(handler.responses), 1)
        self.assertIsInstance(handler.responses[0], StateOfChargeResponse)
        self.assertEqual(handler.responses[0].state_of_charge, 73)

    def test_unsupported_state_of_charge_does_not_block_discovery(self) -> None:
        driver = _VictronMK3Driver()
        driver._variable_id_queue = [13]
        handler = RecordingHandler()

        # A zero scale is the protocol's unsupported-variable response.
        driver._handle_variable_info_response(
            handler,
            bytes([0xFF, ord("X"), 0x8E, 0, 0]),
        )

        self.assertEqual(driver._variable_id_queue, [])
        self.assertIsNone(driver._variable_info[13])


if __name__ == "__main__":
    unittest.main()
