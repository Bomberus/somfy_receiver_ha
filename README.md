# rpi_pico_somfy_blind
Homeassistant integration for rpi pico somfy blinds. To use, clone this entire repo to custom_components subdirectory of your Homessistant configuration directory.

## Configuration
To use this plugin, define each cover as follows in `configuration.yaml`:
  cover:
    - platform: somfy_receiver_ha
      host: 192.168.178.15
      name: terasse
      scan_interval: 15