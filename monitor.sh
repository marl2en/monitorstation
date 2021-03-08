#!/bin/sh
# start monitor program


cd /home/pi/MonitorStation
echo "start monitor program"
echo "Deleting nohup.out"
rm nohup.out
rm nohup*
echo "Deleting log files"
rm -f *.log.*
rm -f *.log
echo "Kill processes then restart"
kill $(ps -ef | grep monitor3.py | awk '{print $2}')
python3 /home/pi/MonitorStation/monitor3.py & #1>&- 2>&-  & #>& /dev/null & 
