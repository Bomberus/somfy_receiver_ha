import json
import logging
from enum import Enum

import async_timeout

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.cover import (
    CoverDevice,
    DEVICE_CLASS_BLIND,
    PLATFORM_SCHEMA,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TIMEOUT

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_TIMEOUT): cv.positive_int,
})


async def _get(hass, host, url, timeout):
    websession = async_get_clientsession(hass)
    resource = "http://{}{}".format(host, url)
    try:
        with async_timeout.timeout(timeout, loop=hass.loop):
            req = await websession.get(resource)
            text_response = await req.text()
            json_response = json.loads(text_response)
            return json_response
    except Exception as e:
        _LOGGER.warning(
            "Unable to get shutter response. "
            "Host name: {}. URL: {}. Original exception: {}".format(
                host, url, e
            )
        )


async def _get_shutter_info(hass, host, timeout):
    url = "/api/device/state"
    response = await _get(hass, host, url, timeout)
    return response.get('device')


async def _get_shutter_settings(hass, host, timeout):
    url = "/api/settings/state"
    response = await _get(hass, host, url, timeout)
    return response.get('settings')


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME, "somfyblinds")
    timeout = config.get(CONF_TIMEOUT) or DEFAULT_TIMEOUT    
    somfyblind = SomfyReceiverBlind(
        host, name=name, timeout=timeout
    )
    async_add_devices([somfyblind])


class SomfyReceiverBlind(CoverDevice):
    _default_name = "SomfyReceiverBlind"

    def __init__(self, host, name=None, timeout=DEFAULT_TIMEOUT):
        self._host = host
        self._name = name
        self._timeout = timeout
        self._state = None
        self._available = False

    @property
    def device_class(self):
        return DEVICE_CLASS_BLIND

    @property
    def name(self):
        return self._name or self._default_name

    @property
    def is_opening(self):
        if self._state:
            return self._state.get('state') == 1
        return False

    @property
    def is_closing(self):
        if self._state:
            return self._state.get('state') == 0
        return False

    @property
    def is_closed(self):
        return self._check_is_closed()

    def _check_is_closed(self):
        if self._state:
            # Blebox built in state indicator doesn't seem reliable
            current_pos = self._state.get('currentPos')
            return current_pos.get('position') >= 95
        return False

    @property
    def current_cover_position(self):
        if self._state:
            position = self._state.get('currentPos').get('position')
            if position:
                return self._invert_position(position)
        return None

    async def async_open_cover(self, **kwargs):
        await self._send_shutter_command("u")

    async def async_close_cover(self, **kwargs):
        await self._send_shutter_command("d")

    async def async_stop_cover(self, **kwargs):
        await self._send_shutter_command("s")

    async def async_set_cover_position(self, **kwargs):
        position = self._invert_position(kwargs['position'])
        await self._send_shutter_command("p", position)

    async def async_update(self):
        shutter_state = await self._get_shutter_state()

        if shutter_state:
            self._state = shutter_state
            self._available = True
        else:
            self._state = None
            self._available = False

    async def _get_shutter_state(self):
        url = "/api/shutter/state"
        response = await _get(self.hass, self._host, url, self._timeout)
        if response:
            return response.get('shutter')
        return None

    async def _send_shutter_command(self, command, parameter=None):
        url = "/s/{}".format(command)
        if parameter is not None:
            url = "{}/{}".format(url, parameter)
        response = await _get(self.hass, self._host, url, self._timeout)
        if response:
            return response.get('shutter')
        return None

    def _invert_position(self, raw_position):
        return -raw_position + 100

    def _get_supported_features(self):
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION

    @property
    def supported_features(self):
        return self._get_supported_features()