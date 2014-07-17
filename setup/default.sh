#!/bin/bash
echo `date`
echo "Starting default.sh - joining wifi network"

sudo ifdown wlan0

sudo service hostapd stop

sudo service dnsmasq stop

sudo cp /etc/network/interfaces /etc/network/interfaces.bak
sudo cp /var/www/setup/interfaces_default /etc/network/interfaces

#sudo service networking restart

sudo ifup wlan0
sudo service avahi-daemon restart

sudo service ispresso restart
