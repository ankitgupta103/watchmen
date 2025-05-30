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