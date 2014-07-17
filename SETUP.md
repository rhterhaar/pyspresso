#Installation of iSPRESSO software on Raspberry Pi

##Installation of Raspberry PI / Debian - Raspbian

<http://elinux.org/RPi_Easy_SD_Card_Setup>


##Get Wireless up and running:

Edit /etc/network/interfaces, remove what’s there, and add:

```
auto lo
iface lo inet loopback
iface eth0 inet dhcp
allow-hotplug wlan0
auto wlan0
iface wlan0 inet dhcp
  wpa-ssid "ssid"
  wpa-psk "password"
```

##Setup Zeroconfig:

Set a clever  hostname from the raspi-config or using "hostname" executable.  Your system will broadcast its 
name on your local network as hostname.local for avahi (linux) or bonjour (apple) aware clients.

```
sudo apt-get install avahi-daemon
```

##Setting up Python:

```
sudo apt-get update
sudo apt-get install python-dev python-setuptools python-pip git
sudo pip install web.py
sudo pip install simplejson
sudo easy_install -U distribute
```

To enable i2c:

```
sudo apt-get install python-smbus
```

Comment out lines in:
/etc/modprobe.d/raspi-blacklist.conf

To enable temp sensor and i2c, add lines to /etc/modules:

for i2c
```
i2c-bcm2708
i2c-dev
```

To enable 1-wire temp sensor, modprobe these, and add to /etc/modules:

```
w1-gpio
w1-therm
```

##Downloading code from GIT:

Create www directory, and clone the code:

```
sudo mkdir /var/www
cd /var/www

sudo git clone https://veggiebenz@bitbucket.org/veggiebenz/pyspresso.git

 # move stuff up one directory, to /var/www/
cd pyspresso
shopt -s dotglob
sudo cp * .. -R
cd ..
shopt -u dotglob
sudo rm -rf pyspresso
 # change ownership of files
sudo chown pi * -R
sudo chgrp pi * -R

 # set up the init script
sudo cp ./initscript/ispresso /etc/init.d/
sudo chmod +x /etc/init.d/ispresso
sudo update-rc.d ispresso defaults
```

##Now on to the wiring!

![Fritzing breadboard diagram](http://bitbucket.org/veggiebenz/pyspresso/raw/master/img/ispresso2_bb.png)



