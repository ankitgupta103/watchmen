# Installation Requirment:

```bash
sudo raspi-config
```
* Enable the spi interface

## or it can be done through 
```bash
sudo nano /boot/firmware/config.txt
add these
dtparam=spi=on
```

* Reboot
```bash
sudo reboot now
```

```bash
sudo apt update
sudo apt install python3-pip
pip3 install spidev RPi.GPIO
```

* If it conflict with the custom gpio config, use venv