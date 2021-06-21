# monitorstation
A Raspberry Pi powered by a solar panel

The main software is located in monitor3.py
It may look complicated, but everything is straight forward:
Read config file.
Set up log file. 
Load battery files (voltage, capacity, energy) as numpy arrays. 
Start a monitor thread (runs in background) to monitor every minute (or other interval) all values that should be measured or logged. 
Save values in a csv-file (comma seperated file) for further analysis. 
AnalyzeData and AnalyzeLastDays are functions to calculate and estimate power consumption and production.  

- Create a directory /home/pi/MonitorStation
- Copy monitor3.py, monitor.sh, all numpy files (.npy) and config.json to it. 
- Edit config.json: your telegram token and chat_id (from your telegram app in your mobile), battery is a lead battery (12V, 12Ah), adjust battery factor, standby current to your system. 
- WittyPi is needed because: operation 24/7 is not possible under winter time. Only one hour per day works here (Sweden). 
- WittyPi extracts needed values (battery voltage, output voltage to RPi and current)
- in the wittypi folder (after installation of wittypi) edit afterStartup.sh and insert: 
/home/pi/wittypi/syncTime.sh 
/home/pi/MonitorStation/monitor.sh
- place WittyPi.py (a python library for wittypi) into wittypi folder. Look here: https://github.com/marl2en/wittypi4python

![IMG_6013](https://user-images.githubusercontent.com/74545075/110316453-0c0b6100-800b-11eb-89da-db5f9a44bfba.jpg)


- Via telegram you get some nice pics and status information. 
(sorry wrong spelling)

![battery](https://user-images.githubusercontent.com/74545075/110317042-dca92400-800b-11eb-9ba4-3b8a85fface9.png)

Here is a plot of battery voltage over 5 periods. The x-axis are number of measurements (every minute over one hour = 60 values per period)
Y-axis is actual battery voltage. 
The red dotted lines are shutdown periods of 23 or 59 hours. Voltage drops like a stone under standby period of 59 hours because of no solar power production and still consumption of 25mA all the time.  Fossil energy from power grid is needed to save this battery. 


!!! For more information look at the pdf file !!!
