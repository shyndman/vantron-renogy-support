Updates Home Assistant of changes to our van's electrical system via MQTT.

### Bluetooth Controller Settings

I've been having a bit of trouble with the BT controller, but this config
appears to work:

```
[bluetooth]# hci0 new_settings: powered bondable ssp br/edr le secure-conn
```
