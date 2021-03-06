"""deCONZ lock platform tests."""
from copy import deepcopy

from homeassistant.components import deconz
import homeassistant.components.lock as lock
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED
from homeassistant.setup import async_setup_component

from .test_gateway import DECONZ_WEB_REQUEST, setup_deconz_integration

from tests.async_mock import patch

LOCKS = {
    "1": {
        "etag": "5c2ec06cde4bd654aef3a555fcd8ad12",
        "hascolor": False,
        "lastannounced": None,
        "lastseen": "2020-08-22T15:29:03Z",
        "manufacturername": "Danalock",
        "modelid": "V3-BTZB",
        "name": "Door lock",
        "state": {"alert": "none", "on": False, "reachable": True},
        "swversion": "19042019",
        "type": "Door Lock",
        "uniqueid": "00:00:00:00:00:00:00:00-00",
    }
}


async def test_platform_manually_configured(hass):
    """Test that we do not discover anything or try to set up a gateway."""
    assert (
        await async_setup_component(
            hass, lock.DOMAIN, {"lock": {"platform": deconz.DOMAIN}}
        )
        is True
    )
    assert deconz.DOMAIN not in hass.data


async def test_no_locks(hass):
    """Test that no lock entities are created."""
    gateway = await setup_deconz_integration(hass)
    assert len(gateway.deconz_ids) == 0
    assert len(hass.states.async_all()) == 0


async def test_locks(hass):
    """Test that all supported lock entities are created."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["lights"] = deepcopy(LOCKS)
    gateway = await setup_deconz_integration(hass, get_state_response=data)
    assert "lock.door_lock" in gateway.deconz_ids
    assert len(hass.states.async_all()) == 1

    door_lock = hass.states.get("lock.door_lock")
    assert door_lock.state == STATE_UNLOCKED

    state_changed_event = {
        "t": "event",
        "e": "changed",
        "r": "lights",
        "id": "1",
        "state": {"on": True},
    }
    gateway.api.event_handler(state_changed_event)
    await hass.async_block_till_done()

    door_lock = hass.states.get("lock.door_lock")
    assert door_lock.state == STATE_LOCKED

    door_lock_device = gateway.api.lights["1"]

    with patch.object(door_lock_device, "_request", return_value=True) as set_callback:
        await hass.services.async_call(
            lock.DOMAIN,
            lock.SERVICE_LOCK,
            {"entity_id": "lock.door_lock"},
            blocking=True,
        )
        await hass.async_block_till_done()
        set_callback.assert_called_with("put", "/lights/1/state", json={"on": True})

    with patch.object(door_lock_device, "_request", return_value=True) as set_callback:
        await hass.services.async_call(
            lock.DOMAIN,
            lock.SERVICE_UNLOCK,
            {"entity_id": "lock.door_lock"},
            blocking=True,
        )
        await hass.async_block_till_done()
        set_callback.assert_called_with("put", "/lights/1/state", json={"on": False})

    await gateway.async_reset()

    assert len(hass.states.async_all()) == 0
