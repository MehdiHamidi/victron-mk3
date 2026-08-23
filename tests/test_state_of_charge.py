import asyncio
import unittest

from victron_mk3 import (
    Handler,
    PowerResponse,
    StateOfChargeResponse,
    _VictronMK3Driver,
)

# RAM variable 13 reports scale 0.005 and offset 0, so a raw value of 200
# represents 1.0, or 100 percent.
SOC_SCALE_INFO = bytes([0xFF, ord("X"), 0x8E, 0x38, 0x7F, 0x8F, 0, 0])
SOC_RAW_FULL = [200, 0]


class RecordingHandler(Handler):
    def __init__(self) -> None:
        self.responses = []

    def on_response(self, response) -> None:
        self.responses.append(response)

    def of_type(self, cls):
        return [x for x in self.responses if isinstance(x, cls)]


def make_driver(state_of_charge_supported: bool = True) -> _VictronMK3Driver:
    """Builds a driver whose RAM variable discovery has already completed."""
    driver = _VictronMK3Driver()
    driver._variable_id_queue = []
    for id in _VictronMK3Driver.REQUIRED_VARIABLE_IDS:
        driver._variable_info[id] = _VictronMK3Driver.VariableInfo(True, 1, 0)
    driver._variable_info[13] = (
        _VictronMK3Driver.VariableInfo(False, 0.005, 0)
        if state_of_charge_supported
        else None
    )
    return driver


def capture_frames(driver: _VictronMK3Driver) -> list:
    frames = []
    driver._send_frame = lambda command, data: frames.append((command, list(data)))
    return frames


def reply(driver: _VictronMK3Driver, payload: list) -> bytes:
    """Builds the reply frame for the request the driver most recently sent."""
    return bytes([0xFF, ord(["X", "Y", "Z"][driver._w_nonce])] + payload)


def exchange(driver: _VictronMK3Driver, handler: Handler, request, payload: list):
    """Runs a request coroutine and feeds it the given reply payload."""

    async def scenario():
        task = asyncio.ensure_future(request())
        await asyncio.sleep(0)
        driver._handle_frame(handler, reply(driver, payload))
        return await task

    return asyncio.run(scenario())


class StateOfChargeTests(unittest.TestCase):
    def test_state_of_charge_rides_along_with_the_power_request(self) -> None:
        driver = make_driver()
        handler = RecordingHandler()
        frames = capture_frames(driver)

        response = exchange(
            driver,
            handler,
            driver.send_power_request,
            [0x85, 10, 0, 20, 0, 30, 0] + SOC_RAW_FULL,
        )

        # A single command carries all four RAM variables.
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0][1], [0x30, 14, 15, 16, 13])
        self.assertIsInstance(response, PowerResponse)
        self.assertEqual(response.state_of_charge, 100)
        # The state of charge is also delivered on its own for handlers that want it.
        self.assertEqual(len(handler.of_type(StateOfChargeResponse)), 1)
        self.assertEqual(handler.of_type(StateOfChargeResponse)[0].state_of_charge, 100)

    def test_state_of_charge_request_reuses_the_combined_read(self) -> None:
        driver = make_driver()
        handler = RecordingHandler()
        capture_frames(driver)
        exchange(
            driver,
            handler,
            driver.send_power_request,
            [0x85, 10, 0, 20, 0, 30, 0] + SOC_RAW_FULL,
        )

        frames = capture_frames(driver)
        response = asyncio.run(driver.send_state_of_charge_request())

        # No further round-trip is needed.
        self.assertEqual(frames, [])
        self.assertEqual(response.state_of_charge, 100)

    def test_unsupported_state_of_charge_is_omitted_from_the_power_request(
        self,
    ) -> None:
        driver = make_driver(state_of_charge_supported=False)
        handler = RecordingHandler()
        frames = capture_frames(driver)

        response = exchange(
            driver, handler, driver.send_power_request, [0x85, 10, 0, 20, 0, 30, 0]
        )

        self.assertEqual(frames[0][1], [0x30, 14, 15, 16])
        self.assertIsNone(response.state_of_charge)
        self.assertIsNone(asyncio.run(driver.send_state_of_charge_request()))

    def test_truncated_reply_falls_back_to_a_separate_request(self) -> None:
        driver = make_driver()
        handler = RecordingHandler()
        capture_frames(driver)

        # The interface answers a four variable request with only three values.
        response = exchange(
            driver, handler, driver.send_power_request, [0x85, 10, 0, 20, 0, 30, 0]
        )

        # The power variables still decode, and the state of charge is dropped.
        self.assertEqual(response.dc_power, 10)
        self.assertIsNone(response.state_of_charge)
        self.assertFalse(driver._combined_state_of_charge_read)

        # Subsequent polls ask for the two sets of variables separately.
        frames = capture_frames(driver)
        exchange(driver, handler, driver.send_power_request, [0x85, 10, 0, 20, 0, 30, 0])
        self.assertEqual(frames[-1][1], [0x30, 14, 15, 16])

        frames = capture_frames(driver)
        soc = exchange(
            driver,
            handler,
            driver.send_state_of_charge_request,
            [0x85] + SOC_RAW_FULL,
        )
        self.assertEqual(frames[-1][1], [0x30, 13])
        self.assertEqual(soc.state_of_charge, 100)

    def test_variable_not_supported_reply_stops_requesting_state_of_charge(self) -> None:
        driver = make_driver()
        handler = RecordingHandler()
        capture_frames(driver)

        async def scenario():
            task = asyncio.ensure_future(driver.send_power_request())
            await asyncio.sleep(0)
            # 0x90 means the device refuses to report one of the requested variables.
            driver._handle_frame(handler, reply(driver, [0x90, 0, 0, 0, 0, 0, 0, 0, 0]))
            return await asyncio.wait_for(task, 0.1)

        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run(scenario())

        self.assertIsNone(driver._variable_info[13])
        self.assertIsNone(asyncio.run(driver.send_state_of_charge_request()))

    def test_zero_scale_marks_a_variable_as_unsupported(self) -> None:
        driver = _VictronMK3Driver()
        driver._variable_id_queue = [13]
        handler = RecordingHandler()
        capture_frames(driver)

        # A zero scale is the protocol's unsupported-variable response.
        driver._handle_variable_info_response(
            handler, bytes([0xFF, ord("X"), 0x8E, 0, 0])
        )

        self.assertEqual(driver._variable_id_queue, [])
        self.assertIsNone(driver._variable_info[13])

    def test_responses_are_withheld_until_discovery_completes(self) -> None:
        driver = _VictronMK3Driver()
        handler = RecordingHandler()
        capture_frames(driver)

        # Discovery is still outstanding, so nothing can be decoded yet.
        self.assertFalse(driver._ensure_variable_info_available())

        driver._variable_id_queue = []
        for id in _VictronMK3Driver.REQUIRED_VARIABLE_IDS:
            driver._variable_info[id] = _VictronMK3Driver.VariableInfo(True, 1, 0)
        self.assertTrue(driver._ensure_variable_info_available())


if __name__ == "__main__":
    unittest.main()
