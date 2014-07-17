#!/bin/bash

echo `date`
echo "Starting setup.sh - setting up ispresso access point"
#sudo cp isc-dhcp-server /etc/default/
sudo cp dnsmasq.conf /etc/
sudo cp dhcpd.conf /etc/dhcp
sudo cp interfaces_setup /etc/network/interfaces
sudo cp hostapd.conf /etc/hostapd/hostapd.conf
sudo cp hostapd.init /etc/init.d/hostapd

sudo ifdown wlan0
sleep 2

sudo ifconfig wlan0 up 10.0.0.1 netmask 255.255.255.0
sleep 2

sudo service avahi-daemon restart

#sudo service dnsmasq start
sleep 2

sudo service hostapd start
#hostapd hostapd.conf &

sleep 2
sudo service dnsmasq start

