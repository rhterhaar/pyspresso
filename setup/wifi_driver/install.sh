
cd RTL8*
cd wpa_supp*
sudo tar -xvf wpa_supplicant_hostapd*
cd wpa_supplicant_hostapd*
cd hostapd
sudo make
sudo make install
# i'ts actually in /usr/local/bin/
#sudo mv hostapd /usr/sbin/hostapd
#sudo chown root.root /usr/sbin/hostapd
#sudo chmod 755 /usr/sbin/hostapd


