########################## monitor.py ####################################
# Lan 192.168.0.219
# wlan 192.168.0.166
# nohup python3 /home/pi/monitor.py & #1>&- 2>&-  & 
# sudo ps -ef | grep python3
# only wittypi for data input
# install libraries
# sudo pip3 install numpy matplotlib scipy sklearn pandas
# sudo apt-get install python3-pip python3-dev
# sudo apt-get install libatlas-base-dev
# sudo pip3 install statsmodels
# sudo pip3 install pytz

############### HOW TO SET UP THE DHT11 HUMIDITY SENSOR ON THE RASPBERRY PI
# https://www.circuitbasics.com/how-to-set-up-the-dht11-humidity-sensor-on-the-raspberry-pi/

# connect sensor
# Pin:  1       2           3
#       Sig     Vcc (5V)    Gnd
# Signal connects to GPIO Pin 7 @ Pi: GPIO 4 (GPIO_GCLK)
# 10 kOhm Pullup resistor between signal and Vcc
# install
# sudo apt-get install git-core
# git clone https://github.com/adafruit/Adafruit_Python_DHT.git
# cd Adafruit_Python_DHT
# sudo apt-get install build-essential python-dev
# sudo python setup.py install # install library
# sudo python3 setup.py install # install library

# i2cdetect -y 1

import sys
import time
import csv
import numpy as np
import matplotlib.pyplot as plt # sudo pip3 install matplotlib
import pandas as pd  # sudo pip3 install pandas
import datetime as dt
import matplotlib.dates as mdates
from matplotlib.dates import MONDAY, DateFormatter, DayLocator, WeekdayLocator
import statsmodels.api as sm
import subprocess 
from PIL import Image, ImageStat
from picamera import PiCamera
import json
import logging, logging.config
from threading import Thread, current_thread, Event 
import pytz
local_tz = pytz.timezone('Europe/Stockholm')
utc_tz = pytz.timezone('UTC')

save_path = "/home/pi/MonitorStation/"

import sys
import os
sys.path.append("/home/pi/wittypi")


from Wittypi import *

import telegram # sudo pip3 install telegram
#from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, RegexHandler # sudo pip3 install python-telegram-bot
from typing import Dict
from telegram import ReplyKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, ConversationHandler #, RegexHandler 




####
"""
import Adafruit_DHT

humidity, temperature = Adafruit_DHT.read_retry(11, 26) # pin board 26 instead of 4
print( 'Temp: {0:0.1f} C  Humidity: {1:0.1f} %'.format(temperature, humidity))
###
import Adafruit_DHT #Import DHT Library for sensor

sensor_name = Adafruit_DHT.DHT11 #we are using the DHT11 sensor
sensor_pin = 17 #The sensor is connected to GPIO17 on Pi

humidity, temperature = Adafruit_DHT.read_retry(sensor_name, sensor_pin) #read from sensor and save respective values in temperature and humidity varibale  


import Adafruit_DHT

Adafruit_DHT.read_retry(11, 26) #26,25,28
Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 26) 

import Adafruit_DHT
Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 27) #pin 13

"""




################################################## telegram section ############################################


def telegram_send_message(message):
    try:
        bot.sendMessage(chat_id=config["telegram_chat_id"], parse_mode='Markdown', text=message, timeout=10)
        logging.info('Telegram message Sent: "%s"' % message)
        return True
    except Exception as e:
        logging.error('Telegram message failed to send message "%s" with exception: %s' % (message, e))
        return False

#telegram_send_message('hello')

def telegram_send_file(file_path):
    filename, file_extension = os.path.splitext(file_path)
    chat_id=config["telegram_chat_id"]
    try:
        if file_extension == '.mp4':
            bot.sendVideo(chat_id=chat_id, video=open(file_path, 'rb'), timeout=30)
        elif file_extension == '.gif':
            bot.sendDocument(chat_id=chat_id, document=open(file_path, 'rb'), timeout=30)
        elif file_extension == '.jpeg':
            bot.sendPhoto(chat_id=chat_id, photo=open(file_path, 'rb'), timeout=10)
        elif file_extension == '.jpg':
            bot.sendPhoto(chat_id=chat_id, photo=open(file_path, 'rb'), timeout=10)
        elif file_extension == '.png':
            bot.sendPhoto(chat_id=chat_id, photo=open(file_path, 'rb'), timeout=10)
        elif file_extension == '.ogg':
            bot.sendVoice(chat_id=chat_id, voice=open(file_path, 'rb'), timeout=10)
        elif file_extension == '.mp3':
            bot.sendVoice(chat_id=chat_id, voice=open(file_path, 'rb'), timeout=10) #audio=open
        else:
            logging.error('Unknown file not sent: %s' % file_path)
        logging.info('Telegram file sent: %s' % file_path)
        return True
    except Exception as e:
        logging.error('Telegram failed to send file %s with exception: %s' % (file_path, e))
        return False

#telegram_send_file('/home/pi/Documents/MonitorStation/fourDaysMonitoringBatteryVolt.png')

def readable_delta(then):
    now=time.time()
    delta = now - then
    days = int(delta/86400)
    delta = delta % 86400
    hours = int(delta/3600)
    delta = delta % 3600
    minutes = int(delta/60)
    seconds = int(delta % 60)
    text = '%sd %s:%s:%s' % (days,hours,minutes,seconds)
    return text

def telegram_bot(token):
    """ parse_mode:HTML  <b>bold</b>, <strong>bold</strong> <i>italic</i>, <em>italic</em> <a href="http://www.example.com/">inline URL</a> <code>inline fixed-width code</code> 
    <pre>pre-formatted fixed-width code block</pre>"""
    global config
    CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)
    schedule = ['Startup','Shutdown']
    voltage_threshold = ['Low Voltage','High Voltage']
    def facts_to_str(user_data: Dict[str, str]) -> str:
        facts = list()
        for key, value in user_data.items():
            facts.append('{} - {}'.format(key, value))
        return "\n".join(facts).join(['\n', '\n'])
    def settings(update: Update, context: CallbackContext) -> int:
        reply_keyboard = [schedule,voltage_threshold ,['Done']]
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        update.message.reply_text(
            "Change settings for schedule or "
            "Voltage threshold",
            reply_markup=reply_markup)
        return CHOOSING
    def regular_choice(update: Update, context: CallbackContext) -> int:
        text = update.message.text
        context.user_data['choice'] = text
        if text in schedule:
            update.message.reply_text(
                '{}: Format DD HH:MM\n DD can be ?? for daily startup or shutdown\n HH = ?? means start or stop every hour'.format(text.lower()))
        elif text in voltage_threshold:
            update.message.reply_text('{}: Format VV.V like 12.1'.format(text.lower()))
        else:
            update.message.reply_text('{}: Cannot find'.format(text.lower()))
        return TYPING_REPLY
    def received_information(update: Update, context: CallbackContext) -> int:
        reply_keyboard = [schedule,voltage_threshold ,['Done']]
        reply_markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        DateList = [x for x in range(1,32)] + ['??']
        HourList = [x for x in range(0,24)] + ['??']
        MinuteList = [x for x in range(0,60)]
        user_data = context.user_data
        text = update.message.text
        category = user_data['choice']
        user_data[category] = text
        del user_data['choice']
        if category in schedule: 
            try:
                date_time = text.split(' ')
                Date = date_time[0]; Time= date_time[1].split(':')
                Hour = Time[0]; Minute = int(Time[1])
                if Date != '??': Date = int(Date)
                if Hour != '??':Hour = int(Hour)
                #print(Date,Hour,Minute)
                if (Date in DateList) and (Hour in HourList) and (Minute in MinuteList): #(len(date_time) == 2) and (len(Time) == 2) and 
                    logging.info('Legimitate input for schedule: %s' % text)
                    update.message.reply_text("Setting changed for {} to {}\n Type 'Done' to affirm".format(category,text),reply_markup=ReplyKeyboardRemove()) # ,reply_markup=reply_markup 
                    return TYPING_REPLY
                else:
                    update.message.reply_text("Settings are wrong for {} to {}".format(category,text),reply_markup=reply_markup) 
                    logging.info('Day: %s Hour:%s Minute:%s' % (str(Date),str(Hour),str(Minute)))
                    return CHOOSING
            except Exception as e:
                logging.info('Error occured: %s' % e)
                update.message.reply_text("Settings are wrong",reply_markup=reply_markup) 
                return CHOOSING
        if category in voltage_threshold: 
            try: 
                volt = float(text)
                if (len(text)== 4) and (11. < volt < 13):
                    logging.info('Legimitate input for schedule: %s' % text)
                    update.message.reply_text("Setting changed for {} to {}\n Type 'Done' to affirm or \n 'Cancel' to cancel".format(category,text),reply_markup=ReplyKeyboardRemove()) # ,reply_markup=reply_markup
                    return TYPING_REPLY
                else:
                    update.message.reply_text("Settings are wrong",reply_markup=reply_markup) 
                    return CHOOSING
            except Exception as e:
                logging.info('Error occured: %s' % e)
                update.message.reply_text("Settings are wrong",reply_markup=reply_markup) 
                return CHOOSING
    def done(update: Update, context: CallbackContext) -> int:
        user_data = context.user_data
        if 'choice' in user_data: del user_data['choice']
        print('user_data',user_data)
        update.message.reply_text("This settings are changed:" "{}" "Now excecuting command".format(facts_to_str(user_data)),reply_markup=ReplyKeyboardRemove())
        for k,v in user_data.items():
            if k == 'Startup': 
                if set_startup_time(stringtime=v): update.message.reply_text("Setting {} to {}".format(k,v),) 
                else: update.message.reply_text("Failed to set {} to {}".format(k,v),) 
            if k == 'Shutdown': 
                if set_shutdown_time(stringtime=v): update.message.reply_text("Setting {} to {}".format(k,v),) 
                else: update.message.reply_text("Failed to set {} to {}".format(k,v),) 
            if k == 'Low Voltage': 
                if set_low_voltage_threshold(volt=v): update.message.reply_text("Setting {} to {}".format(k,v),) 
                else: update.message.reply_text("Failed to set {} to {}".format(k,v),) 
            if k == 'High Voltage': 
                if set_recovery_voltage_threshold(volt=v): update.message.reply_text("Setting {} to {}".format(k,v),) 
                else: update.message.reply_text("Failed to set {} to {}".format(k,v),) 
        user_data.clear()
        return ConversationHandler.END
    def prepare_status():
        return '*STATUS*\nStarted: _%s_\nLast Measure: _%s_\nStart Analyse: _%s ago_\nMeasure Interval: _%s min_\nAnalyse Interval: _%s min_\nNumber of Days: _%s_\nLast Analyse: _%s_\nNext Startup at: _%s_\nNext Startup in: _%s_\nNext Shutdown at: _%s_\nNext Shutdown in: _%s_\nCPU Load: _%s_' % (
                readable_delta(config["start_time"]),
                readable_delta(config["last_measured"]),
                readable_delta(config["starttime_analyze"]),
                str(config["monitor time interval"]),
                str(config["analyze interval"]),
                str(config["days"]),
                config["analyze data"]["Last timestamp str"],
                config["next startup"]['startup_time str'],
                config["next startup"]['startup_time delta str'],
                config["next shutdown"]['shutdown_time str'],
                config["next shutdown"]['shutdown_time delta str'],
                str(config["CPU_load"])
            )
    def prepare_status_environment():
        return '*EVIRONMENT STATUS*\nBrightness:_%s_\nCPU_Temp:_%s_\nRPi_Temp:_%s_\nLast Measured:_%s ago_' % (
                str(config["Brightness"]), 
                str(config["CPU_Temp"]), 
                str(config["RPi_Temp"]), 
                readable_delta(config["last_measured"])
            )
    def prepare_status_powermanagement():
        return '*POWER MANAGEMENT*\nBattery_Voltage: _%s V_\nBattery_Capacity: _%s procent_\nBattery_Energy _%s procent_\nRPI_Power: _%s W_\nGained_Capacity: _%s since %s_\nGained_Energy: _%s since %s_\nLast Measured: _%s ago_\nLast Analysed: _%s_\nBattery Capacity: _%s Ah_' % (
                str(config["Battery_Volt"]),
                str(round(config["Battery_Capacity"],2)),
                str(round(config["Battery_Energy"],2)),
                str(round(config["RPI_Power"],2)),
                str(round(config["Gained_Capacity"],2)),
                readable_delta(config["starttime_analyze"]),
                str(round(config["Gained_Energy"],2)),
                readable_delta(config["starttime_analyze"]),
                readable_delta(config["last_measured"]),
                config["analyze data"]["Last timestamp str"],
                str(config["BatteryCapacity"])
            )
    def start(update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
    def photo(update, context):  
        config['camera_mode'] = 'photo' #'mp4'
        file_name = save_path + "photo-" + dt.datetime.now().strftime("%Y-%m-%d-%H%M%S") + '.jpg'
        outputfile = get_photo_video(file_name,getBrightness=False)
        if outputfile != '': telegram_send_file(outputfile)
        else: context.bot.send_message(chat_id=update.effective_chat.id, text="Unable to take a picture")
    def video(update, context):  
        config['camera_mode'] = 'mp4' 
        file_name = save_path + "video-" + dt.datetime.now().strftime("%Y-%m-%d-%H%M%S") + '.h264'
        outputfile = get_photo_video(file_name,getBrightness=False)
        if outputfile != '': telegram_send_file(outputfile)
        else: context.bot.send_message(chat_id=update.effective_chat.id, text="Unable to record video")
    def help(update, context):
        text = " The following commands are available:\n"
        commands = [["/status", "Request status"],
                    ["/statusenvironment", "Request environment status"],
                    ["/statuspowermanagement", "Power management"],
                    ["/getLowVoltageThreshold", "Voltage for shutdown"],
                    ["/getRecoveryVoltageThreshold", "Voltage to startup"],
                    ["/getLocalTime", "Get RPi Local Time"],
                    ["/settings", "change schedule or voltage threshold"],
                    ["/help", "Get this message"],
                    ["/photo", "Take photo. Switch to photo mode"],
                    ["/video", "Record video. Switch to video mode"],
                    ["/set", "Set monitor time interval in minutes"],]
        for command in commands: text += command[0] + " " + command[1] + "\n"
        #bot.sendMessage(update.message.chat_id, parse_mode='Markdown',text='/status: Request status\n/statusenvironment: Request environment status\n/statuspowermanagement: Request Power Management Status\n/getLowVoltageThreshold: \n/getRecoveryVoltageThreshold: ', timeout=10)
        #context.bot.send_message(chat_id=update.effective_chat.id,parse_mode='Markdown',text='/status: Request status\n/statusenvironment: Request environment status\n/statuspowermanagement: Request Power Management Status\n/getLowVoltageThreshold: \n/getRecoveryVoltageThreshold: ', timeout=10)
        context.bot.send_message(chat_id=update.effective_chat.id,parse_mode='Markdown',text=text, timeout=10)
    def status(update: Update, context: CallbackContext): # status(update: Update, context: CallbackContext):
        #if check_chat_id(update):
        #chat_id = update.message.chat_id
        #update.message.reply_text(prepare_status())
        #update.message.reply_markup(prepare_status())
        #bot.sendMessage(update.message.chat_id, parse_mode='Markdown', text=prepare_status(), timeout=10)
        text = prepare_status()
        context.bot.send_message(chat_id=update.effective_chat.id,parse_mode='Markdown',text=text)
        #telegram_send_message(text)
    def check_chat_id(update):
        if update.message.chat_id != telegram_chat_id:
            logging.debug('Ignoring Telegam update with filtered chat id %s: %s' % (update.message.chat_id, update.message.text))
            return False
        else: return True
    def set_monitor_time_interval(update: Update, context: CallbackContext) -> None:
        chat_id = update.message.chat_id
        try:
            # args[0] should contain the time for the timer in seconds
            due = int(context.args[0])
            if not (1 < due < 59):
                update.message.reply_text('Sorry wrong value')
                return
            text = 'monitor time interval set to ' + context.args[0]
            config["monitor time interval"] = due
            update.message.reply_text(text)
        except (IndexError, ValueError):
            update.message.reply_text('Monitor Time interval. Usage: /set <minutes>')
    def statusenvironment(update, context):
        #if check_chat_id(update):
        #bot.sendMessage(update.message.chat_id, parse_mode='Markdown', text=prepare_status_environment(), timeout=10)
        context.bot.send_message(chat_id=update.effective_chat.id,parse_mode='Markdown',text=prepare_status_environment())
    def statuspowermanagement(update, context):
        #if check_chat_id(update):
        #update.message.reply_text(prepare_status_powermanagement())
        text = prepare_status_powermanagement()
        context.bot.send_message(chat_id=update.effective_chat.id,parse_mode='Markdown',text=text)
        #telegram_send_message(text)
    def getLowVoltageThreshold(update, context):
        thresh = get_low_voltage_threshold()
        if not 'str' in str(type(thresh)):  thresh = str(thresh)
        telegram_send_message('Low Voltage Threshold: *%s*' % thresh)
        logging.info('Low Voltage Threshold: *%s*' % thresh)
    def getRecoveryVoltageThreshold(update, context):
        #if check_chat_id(update):
        thresh = get_recovery_voltage_threshold()
        if not 'str' in str(type(thresh)):  thresh = str(thresh)
        telegram_send_message('Recovery Voltage Threshold: *%s*' % thresh)
        logging.info('Recovery Voltage Threshold: *%s*' % thresh)
    def getLocalTime(update, context):
        #if check_chat_id(update):
        LocalTime = get_rtc_timestamp()[1].strftime("%Y-%m-%d %H:%M:%S")
        telegram_send_message('LocalTime: *%s*' % LocalTime)
        logging.info('Recovery Voltage Threshold: *%s*' % LocalTime)
    def unknown(update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")
    def cancel(update: Update, context: CallbackContext) -> int:
        user = update.message.from_user
        logger.info("User %s canceled the conversation.", user.first_name)
        update.message.reply_text('Change of settings is canceled.', reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    #def echo(update, context):
    #    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)
    #    logging.info('Received text: *%s*' % update.message.text) 
    #    print(update.message.text)
    #def stop_and_restart():
    #    """Gracefully stop the Updater and replace the current process with a new one"""
    #    updater.stop()
    #    os.execl(sys.executable, sys.executable, *sys.argv)
    #def restart(update, context):
    #    update.message.reply_text('Bot is restarting...')
    #    Thread(target=stop_and_restart).start()
    updater = Updater(token)
    dp = updater.dispatcher
    #echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
    #dp.add_handler(echo_handler)
    dp.add_handler(CommandHandler("start", start))
    #dp.add_handler(CommandHandler('restart', restart)) # , filters=Filters.user(username='@jh0ker'))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("photo", photo))
    dp.add_handler(CommandHandler("video", video))
    dp.add_handler(CommandHandler("set", set_monitor_time_interval))
    dp.add_handler(CommandHandler("statusenvironment", statusenvironment))
    dp.add_handler(CommandHandler("statuspowermanagement", statuspowermanagement))
    dp.add_handler(CommandHandler("getLowVoltageThreshold", getLowVoltageThreshold))
    dp.add_handler(CommandHandler("getRecoveryVoltageThreshold", getRecoveryVoltageThreshold))
    dp.add_handler(CommandHandler("getLocalTime", getLocalTime))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', settings)],
            states={
                CHOOSING: [MessageHandler(Filters.regex('^(Startup|Shutdown|Low Voltage|High Voltage)$'), regular_choice),],
                TYPING_REPLY: [MessageHandler(Filters.text & ~(Filters.command | Filters.regex('^Done$') | Filters.regex('^Cancel$')),received_information,)],
                },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), done),MessageHandler(Filters.regex('^Cancel$'), cancel)],)
    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.command, unknown))
    logging.info("telegram thread running")
    updater.start_polling() # timeout=12
    updater.idle() #ne


###################################################################################################3############

def CheckFolder(directory='directory'):
    """Check if a folder exists and create it if necessary"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logging.debug('Creating folder: %s' % directory)


def EXE2(arguments=[]):
    """Execute os program or script. Arguments are a list [filename,argument1,argument2,...]"""
    if any(arguments):
        #print 'arguments',arguments
        try:
            p = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            return out,err
        except Exception as e:
            logging.error('Error EXE2 %s' % e)
            return None,None


def sortFilesByTime(pcap_files,prefix= 'trace_',suffix='.pcap'):
    """sort files, oldest first"""
    path = pcap_files[0].split( pcap_files[0].split('/')[-1])[0]
    filenames = [x.split(path)[-1] for x in pcap_files]
    date_time = [x.split(prefix)[1].split(suffix)[0] for x in filenames]
    #dfdt = [dt.datetime.strptime(x,'%Y%m%d-%H_%M_%S') for x in date_time]
    dfdt = [dt.datetime.strptime(x,'%Y-%m-%d_%H-%M-%S') for x in date_time]
    x_sort = sorted(dfdt, key=lambda x: x)
    #for i in range(len(x_sort)-1): # print time intervall
    #    print(x_sort[i+1]-x_sort[i])
    #x_str_time = [path+prefix+'{:%Y-%m-%d_%H-%M-%S}'.format(x)+suffix for x in dfdt]
    x_str_time = [path+prefix+'{:%Y-%m-%d_%H-%M-%S}'.format(x)+suffix for x in x_sort]
    return x_str_time,x_sort


def calcNextStartupShutdownTimeAndDelta():
    start_shutdown_dict = {}
    for sstime in ['startup_time','shutdown_time']:
        if sstime == 'startup_time': startup_time_utc,startup_time_local,str_time,timedelta = get_startup_time()
        else: startup_time_utc,startup_time_local,str_time,timedelta = get_shutdown_time()
        #start_shutdown_dict[sstime] = startup_time_local
        #start_shutdown_dict[sstime+' delta'] = timedelta  # str(start_shutdown_dict[sstime+' delta'])  '29 days, 0:54:35'
        start_shutdown_dict[sstime+' str'] = str(startup_time_local).split('.')[0]
        start_shutdown_dict[sstime+' delta str'] = str(timedelta).split('.')[0]
    #logging.info('startup shutdown: %s',str(start_shutdown_dict))
    return start_shutdown_dict


def getClockFreq(para=['arm', 'core']):
    para_list = ['arm', 'core', 'h264', 'isp', 'v3d', 'uart', 'pwm', 'emmc', 'pixel', 'vec', 'hdmi', 'dpi']
    para = [x for x in para if x in para_list]
    outlist = []
    for p in para:
        out = int(str(EXE2(arguments=['vcgencmd', 'measure_clock',p])[0]).split('=')[-1].split("\\")[0])
        outlist.append(out)
    return outlist

def getRPiTemp():
    cpu_temp = float(EXE2(arguments=['cat', '/sys/class/thermal/thermal_zone0/temp'])[0])/1000.
    gpu_temp = float(str(EXE2(arguments=['vcgencmd', 'measure_temp'])[0]).split('=')[-1].split("\'")[0])
    return [cpu_temp, gpu_temp]


def getCPUload():
    out = EXE2(arguments=['iostat', '-o','JSON'])[0]
    cpu_load = round(100. - float(str(out).split('idle": ')[-1].split('},')[0]),2)
    return cpu_load


def smoothCurve(y,show=False,frac=0.1):
    """smooth a curve. y: np array"""
    N = len(y); x = np.linspace(0,N-1,N)
    lowess = sm.nonparametric.lowess(y, x, frac=frac)
    if show:
        plt.plot(x, y, '+')
        plt.plot(lowess[:, 0], lowess[:, 1])
        plt.show()
    return lowess[:, 1]


def saveDict(outdict,filename='/home/pi/MonitorStation/battery.json'):
    with open(filename, 'w') as outfile:
        json.dump(outdict, outfile,sort_keys=True,indent=4) # separators=(',', ': ')

def loadDict(filename='/home/pi/MonitorStation/battery.json'):
    with open(filename) as f:
        dictobj = json.load(f)
    return dictobj


def getFiles(DIR = '/home/usix/test/data/datasets/2019-01-28',suffix = '.csv',substring='__'):
    filelist = []
    for root, dirs, files in os.walk(DIR):
        for f in files:
            if f.endswith(suffix) and (substring in f):
                filelist.append(os.path.join(root, f))
    return filelist



def get_photo_video(output_file,getBrightness=True):
    """ Record video and save to disk. """
    try:
        with PiCamera() as camera:
            camera.hflip = config['camera_hflip']
            camera.vflip = config['camera_vflip']
            if getBrightness:
                camera.resolution = (320, 240)
                camera.capture(output_file)
                return output_file
            else:
                if config['camera_mode'] == 'mp4':
                    camera.resolution = config['video_resolution']
                    camera.start_recording(output_file)
                    camera.wait_recording(config['video_capture_length'])
                    camera.stop_recording()
                    logging.info('record video: %s' % output_file)
                    new_filename = convert_h264_to_mp4(output_file)
                    return new_filename
                else:
                    camera.resolution = config['camera_image_size']
                    camera.capture(output_file)
                    return output_file
    except Exception as e:
        logging.error('Failed to capture camera output because of: %s' % e)
        return '' 


def convert_h264_to_mp4(filename):
    """convert h264 coded video to mp4"""
    name,extention = filename.split('.')
    new_filename = name + '.mp4'
    arguments = ['MP4Box','-fps','30','-add',filename,new_filename] #MP4Box -fps 30 -add my_video.h264 my_video.mp4 | sudo apt-get install -y gpac
    EXE2(arguments)
    logging.debug('converting video to: %s' % new_filename)
    os.remove(filename)
    return new_filename


def getBrightness():
    im_file=config["ImageName"]
    if get_photo_video(output_file=im_file,getBrightness=True) == im_file:
        im = Image.open(im_file).convert('L')
        stat = ImageStat.Stat(im)
        config["Brightness"] = round(stat.rms[0],2)
        return round(stat.mean[0],2), config["Brightness"]
    else:
        return (config["Brightness"],config["Brightness"])


def voltage2energy(act_volt = 11.9):
    """map voltage to energy left in battery, when battery is known"""
    diffvolt = np.absolute(battVolt - act_volt)
    mindiff = diffvolt.min()
    act_idx = diffvolt == mindiff
    act_energy = energy[act_idx][0]
    act_capacity = capacity[act_idx][0]
    act_energy100 = energy100[act_idx][0]
    act_capacity100 = capacity100[act_idx][0]
    return act_energy,act_capacity,act_energy100,act_capacity100



def saveCSV(csvfile='',datalist=[]):
    """Save data list to csv file"""
    with open(csvfile, "w") as output:
        writer = csv.writer(output, lineterminator='\n')
        for val in datalist:
            writer.writerow(val)

def readCSV(csvfile='', mode='rb' ):
    """Read data list from csv file"""
    data = []
    with open(csvfile, mode) as f:
        reader = csv.reader(f, delimiter=',', lineterminator='\n')
        for row in reader:
            data.append(row)
    return data

def saveCSVappend(csvfile='',datalist=[]):
    """Save data list to csv file"""
    with open(csvfile, "a") as output:
        writer = csv.writer(output, lineterminator='\n')
        for val in datalist:
            writer.writerow(val)


def mapper(act_val = 5.9,Energy=True):
    """map energy/capacity to %"""
    if Energy: 
        diff = np.absolute(energy - act_val)
        act_idx = np.argmin(diff)
        return energy100[act_idx]
    else: 
        diff = np.absolute(capacity - act_val)
        act_idx = np.argmin(diff)
        return capacity100[act_idx]


def show(data,filename='/home/pi/data.png',col2sel=[]):
    if not 'pandas' in str(type(data)): db = pd.DataFrame(data[1:], columns=data[0])
    else: db = data
    if col2sel == []: col2sel = [x for x in db.columns.tolist() if not x in config["not2show"]] # ['date time', 'time delta', 'ch 0 value', 'Ch 5 value']
    print(col2sel)
    df = db[col2sel].copy()
    plt.close()
    plt.figure(figsize=(16, 12), dpi=80, facecolor='w', edgecolor='k')
    for col in df.columns: 
        plt.plot(df[col].values, label=col)
    plt.title('Channel Output'); plt.xlabel('Time in sec')
    plt.ylabel('Value'); plt.legend()
    if filename != '': plt.savefig(filename)
    else: plt.show()
    plt.close()


def subPlotDFmultiple(data,datalen2show = 100,filename=''):
    """Plot columns of a panda timeserie in different sub plots"""
    if not 'pandas' in str(type(data)): db = pd.DataFrame(data[1:], columns=data[0])
    else: db = data
    col2sel = [x for x in db.columns.tolist() if not x in config["not2show"]] # ['date time', 'time delta', 'ch 0 value', 'Ch 5 value']
    df = db[col2sel].copy()
    plt.close()
    plt.figure(figsize=(16, 12), dpi=80, facecolor='w', edgecolor='k')
    i = 1
    if datalen2show < len(df): startplot = len(df) - datalen2show
    else: startplot = 0
    for col in df.columns:         
        plt.subplot(len(df.columns), 1, i)
        plt.plot(df[col][startplot:])
        ch = int(col.split(' ')[1])
        if config["channelVoltage"][ch]: label='CH ' + str(ch) + ' in Volt'  # check if channel is voltage or current
        else: label='CH ' + str(ch) + ' in Ampere'
        plt.title(label, y=0.5, loc='right')
        i += 1
    plt.xlabel('Time'); plt.ylabel('Value')
    if filename != '': plt.savefig(filename)
    else: plt.show()
    plt.close()

def setDatetimeIndex(df,index_col='Date'):
    df2 = df.copy()
    if not 'DatetimeIndex' in str(type(df2.index)):
        print('setting datetime index')
        df2.index = pd.to_datetime(df2[index_col])
    return df2


def timeseriesSubplotAll(db,maxlen=500,index_column='date time',plotInOneChart=True,filename = '',col2show =[]):
    if col2show == []: col2show = [x for x in db.columns.tolist() if not x in config["not2show"]] # ['date time', 'time delta', 'ch 0 value', 'Ch 5 value']
    else: col2show = [x for x in col2show if x not in config["not2show"]]
    d_f = db.copy(); plt.close(); intradaychart = True
    if len(db) > maxlen: df2 = db.iloc[-maxlen:].copy()
    else: df2 = db.copy()
    df2 = setDatetimeIndex(df2,index_col=index_column)
    date1 = df2[index_column].iloc[0]
    date2 = df2[index_column].iloc[-1]
    print('date1',date1,'date2',date2)
    #df2 = df2[(df2.index >= date1) & (df2.index <= date2)]
    xl = df2.index.values
    if plotInOneChart:
        mondays = WeekdayLocator(MONDAY)        # major ticks on the mondays
        weekFormatter = DateFormatter('%b %d')
        alldays = DayLocator()              # minor ticks on the days
        dayFormatter = DateFormatter('%d') 
        fig, ax = plt.subplots(figsize=(20, 16))
        for col in col2show:
            try:
                ch = int(col.split(' ')[1])
                if config["channelVoltage"][ch]: label='CH ' + str(ch) + ' in Volt'  # check if channel is voltage or current
                else: label='CH ' + str(ch) + ' in Ampere'
            except: label = col
            ax.plot(xl, df2[col].values, '-o',  label=label) # color='purple',
        ax.set(xlabel=date1 + ' - ' + date2, ylabel="Values", title="Measured Values")
        if not intradaychart:
            ax.xaxis.set_major_locator(mondays)
            ax.xaxis.set_major_formatter(weekFormatter)
            if len(df2) <= 32:
                ax.xaxis.set_minor_locator(alldays)
                ax.xaxis.set_minor_formatter(dayFormatter)
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0,24,1)))
                ax.xaxis.set_minor_formatter(mdates.DateFormatter('%M'))
                ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=range(0,60,15)))
        plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
        plt.grid(True);plt.legend()
    else:
        fig,AX = plt.subplots(nrows=len(col2show), constrained_layout=True,figsize=(22,16))
        for ax,col in zip(AX,col2show):
            timeseriesSubplot(ax,df2,xl,date1,date1,col)
    if filename != '': plt.savefig(filename)
    else: plt.show()
    plt.close()


def timeseriesSubplot(ax,df2,xl,date1,date2,col,intradaychart=True):
    """Time series subplot with x-axis as time"""
    try:
        ch = int(col.split(' ')[1])
        if config["channelVoltage"][ch]: label='CH ' + str(ch) + ' in Volt'  # check if channel is voltage or current
        else: label='CH ' + str(ch) + ' in Ampere'
        print(label)
    except:
        label = col
    mondays = WeekdayLocator(MONDAY)        # major ticks on the mondays
    weekFormatter = DateFormatter('%b %d')
    alldays = DayLocator()              # minor ticks on the days
    dayFormatter = DateFormatter('%d')
    ax.set(xlabel=label + '  ' + date1 + ' - ' + date2, ylabel="Values") # , title="Measured Values"
    ax.plot(xl, df2[col].values, '-o',  color='purple',label=col)
    if not intradaychart:
        ax.xaxis.set_major_locator(mondays)
        ax.xaxis.set_major_formatter(weekFormatter)
        if len(df2) <= 32:
            ax.xaxis.set_minor_locator(alldays)
            ax.xaxis.set_minor_formatter(dayFormatter)
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0,24,1)))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%M'))
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(byminute=range(0,60,15)))
    plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
    plt.grid(True) #;plt.legend()


def monitor():
    global config
    out = calcNextStartupShutdownTimeAndDelta()
    for k,v in out.items():
        if "startup" in k: config["next startup"][k] = v
        if "shutdown" in k: config["next shutdown"][k] = v
    logging.info('next startup %s is in %s',config["next startup"]['startup_time str'],config["next startup"]['startup_time delta str'])
    logging.info('next shutdown %s is in %s',config["next shutdown"]['shutdown_time str'],config["next shutdown"]['shutdown_time delta str'])
    d_f = analyzeLastDays(Show=False)
    #for i,ele in enumerate(['date time', 'DateTime','energy', 'capacity','energy%','capacity%']):
    #    values = d_f[['date time','dt DateTime','calc energy','calc capacity','calc energy%','calc capacity%']].iloc[-1].values.tolist()
    #    battery[ele] = values[i]
    try:
        monitordata = readCSV(save_path + 'monitor.csv', mode='r' ) 
        #for row in monitordata: print( row)
        mdf = pd.DataFrame(monitordata[1:], columns=monitordata[0])
        not2conv = ['date time','DateTime', 'startup_time', 'shutdown_time', 'low_voltage_threshold', 'recovery_voltage_threshold','dt DateTime']
        col2conv = [x for x in mdf.columns.tolist() if x not in not2conv] 
        for col in col2conv: mdf[col] = [float(x) for x in mdf[col].values]
        logging.info('last timestamp for analyze %s',mdf['date time'].iloc[-1])
        monitordata.append(d_f.iloc[-1].values.tolist())
        #for row in monitordata: print( row)
        saveCSV(csvfile=save_path + 'monitor.csv',datalist=monitordata)
    except Exception as e:
        logging.info('failed to load monitor file because of %s',e)
        monitordata = [d_f.columns.tolist(),d_f.iloc[-1].values.tolist()]
        saveCSV(csvfile=save_path + 'monitor.csv',datalist=monitordata)
    #seconds2shutdown = config["next shutdown"]['shutdown_time delta'].total_seconds()
    logging.info('time delta to shutdown %s',config["next shutdown"]['shutdown_time delta str'])


def getTotalSeconds(time_string):
    if 'days' in time_string: days = int(time_string.split(' ')[0]); time_string = time_string.split(' ')[-1]
    else: days = 0
    time_list = time_string.split(':')
    time_list = [int(x) for x in time_list]
    totalseconds = 3600*24*days + 3600*time_list[0] + 60*time_list[1] + time_list[2]
    return totalseconds


def getHighestNumbersReturnIndexes(val,maxnumber = 4):
    """Get indexes of highest numbers in value array"""
    if type(val) == list: val = np.array(val)
    a = val.copy()
    hv = [] # highest value, highest label
    for i in range(0,maxnumber,1):
        if maxnumber > len(a):
            maxnumber = len(a)
        maxix = np.argmax(a)
        maxval = a[maxix]
        org_maxix = np.where(val == maxval)[0][0]
        hv += [org_maxix]
        a = np.delete(a, maxix)
    return sorted(hv)


def analyzeData(df,Show=True):
    db = df.copy()
    not2conv = ['date time','DateTime', 'startup_time', 'shutdown_time', 'low_voltage_threshold', 'recovery_voltage_threshold','dt DateTime']
    col2conv = [x for x in db.columns.tolist() if x not in not2conv] 
    col2smooth = ['input_voltage','output_voltage','outputcurrent' ] #,'Power Consumption','Ah drained','Energy drained in kJ',
    for col in col2conv: db[col] = [float(x) for x in db[col].values] # 'outputcurrent' = current @ battery voltage
    db['outputcurrent'] = db['outputcurrent'] * config['current factor']['outputcurrent']
    for col in col2smooth: db[col] = smoothCurve(db[col].values,show=Show,frac=0.5) # smooth
    if Show: show(db,filename='',col2sel=['outputcurrent' ])
    for col in ['outputcurrent' ]: logging.info('mean curent for:%s is %f', col, round(db[col].mean(),2)) #print(col,db[col].mean())
    db['Power Consumption'] = db['outputcurrent'].values * db['input_voltage'].values # 'output_voltage'  '5VPi'
    db['diff time'] = db['time delta'].diff().fillna(0.)
    db['Solar Power'] = 0.; db['Ah solar']=0.; db['Solar Power calc'] = 0.;db['Energy solar'] = 0.; db['Energy solar calc'] = 0.
    mask = db['brightness'].values > 40 # ~mask
    arr = np.zeros(len(db),dtype=float) 
    arr[mask] = (20./200.) *  db['brightness'].values[mask] * 0.1336290111849018 # 0.24597861272319832 # 20 = max power output of panel, 200 = max brightness
    db['Solar Power'] = arr
    solarCurrentEstbyBrightness = db['Solar Power'].values / 19. # 19V
    #logging.info('solarCurrentEstbyBrightness :%s', str(solarCurrentEstbyBrightness))
    solarCurrentEstbyBrightness = (solarCurrentEstbyBrightness * db['diff time'].values)/3600.
    db['Ah solar'] = np.round(solarCurrentEstbyBrightness.cumsum(),4)
    db['Energy solar']= np.round(((db['Solar Power'].values * db['diff time'].values)/3600.).cumsum(),2) # for Wh
    return db


def analyzeLastDays(Show=True,calcCurrSD=False):
    global config
    days=config["days"]
    startday = dt.datetime.now() - dt.timedelta(days=days)
    files = getFiles(DIR = save_path,suffix = '.csv',substring='__')
    x_str_time,x_sort = sortFilesByTime(files,prefix= 'monitor__',suffix='.csv')
    x_sort2 = [x for x in x_sort if x > startday]
    num_files = len(x_sort2)
    if num_files == 0: num_files=1
    logging.info('number of files to analyze %d for last %d days',num_files,days)
    files2use = x_str_time[-num_files:]
    all_data = []
    for fn in files2use:
        new_data = readCSV(fn, mode='r' ) 
        df = pd.DataFrame(new_data[1:], columns=new_data[0])
        df['dt DateTime'] = [dt.datetime.strptime(x,'%Y-%m-%d %H:%M:%S') for x in df['date time'].values]
        d_f = analyzeData(df,Show=False)
        all_data.append(d_f)
    if len(all_data) > 1: d_f = pd.concat([all_data[0],all_data[1]])
    else: d_f = all_data[0]
    logging.info('time for analyzing')
    config["analyze data"]["last file"] = x_str_time[-1]
    config["analyze data"]["Last timestamp str"] = d_f['date time'].iloc[-1]
    if len(all_data) > 2: 
        for ele in all_data[2:]: d_f = pd.concat([d_f,ele])
    d_f = d_f.reset_index(drop=True)
    d_f['time delta'] = d_f['timestamp'] - d_f['timestamp'].values[0]
    d_f['diff time'] = d_f['time delta'].diff().fillna(0.)
    mask = d_f['diff time'].values > d_f['diff time'].median() * 10. # measure interval 1 min, if 10 times greater because of shutdown?
    hi = getHighestNumbersReturnIndexes(d_f['diff time'].values,maxnumber = mask.sum()) # [564, 1224, 1884, 2544]
    plt.close()
    plt.plot(d_f['input_voltage'].values); 
    for i,ele in enumerate(hi): plt.axvline(x=ele, color = 'red', ls = '--',label='shotdown period for ' + str(round(d_f['diff time'].values[hi][i]/3600.,1)) + 'hours')
    plt.grid(); plt.legend(); plt.savefig(save_path+'battery.png')
    shutdownIndex = [0] + hi # [0, 564, 1224, 1884, 2544]
    print('shutdownIndex',shutdownIndex)
    Ah_drain = np.zeros(len(d_f),dtype=float)
    energy_drain = np.zeros(len(d_f),dtype=float)
    for i,e in enumerate(shutdownIndex):
        if e == shutdownIndex[-1]:
            Ah_drain[e+1:] = d_f['outputcurrent'].values[e+1:] * d_f['diff time'].values[e+1:]/3600. 
            energy_drain[e+1:] = d_f['Power Consumption'].values[e+1:] * d_f['diff time'].values[e+1:]/3600. # Wh instead of kJ (1000)
        else:
            Ah_drain[e+1:shutdownIndex[i+1]-1] = d_f['outputcurrent'].values[e+1:shutdownIndex[i+1]-1] * d_f['diff time'].values[e+1:shutdownIndex[i+1]-1]/3600.
            energy_drain[e+1:shutdownIndex[i+1]-1] = d_f['Power Consumption'].values[e+1:shutdownIndex[i+1]-1] * d_f['diff time'].values[e+1:shutdownIndex[i+1]-1]/3600. # Wh, not kJ
    Ah_drain = np.round(Ah_drain.cumsum(),2)
    energy_drain = np.round(energy_drain.cumsum(),2)
    ## energy consumption under shutdown
    if calcCurrSD:
        startupIndex = np.array(hi)
        shutdownIndex = np.array(hi) - 1
        voltShutdown = d_f['input_voltage'].values[shutdownIndex] # array([12.53824428, 12.2842118 , 12.0303937 ])
        voltStartup = d_f['input_voltage'].values[startupIndex] # array([12.50040067, 12.23645535, 11.99220522])
        datalistSD = [voltage2energy(ele) for ele in voltShutdown]
        datalistSU = [voltage2energy(ele) for ele in voltStartup]
        capacitySD = np.array([x[1] for x in datalistSD])
        capacitySU = np.array([x[1] for x in datalistSU])
        deltacapacity = capacitySD - capacitySU
        print('deltacapacity',deltacapacity)
        currSD_calc = (deltacapacity*3600.)/d_f['diff time'].values[startupIndex]
        print('currSD_calc',currSD_calc,'mean',currSD_calc.mean())
    currSD = config["standby_current"] # 0.01 #0.0314305525 # A current while RPi is shutdown
    d_f['Energy RPi'] = energy_drain * -1.
    d_f['Ah RPi'] = Ah_drain * -1.
    Ah_standby = np.zeros(len(d_f),dtype=float)
    energy_standby = np.zeros(len(d_f),dtype=float)
    Ah_standby = currSD * d_f['diff time'].values/3600.
    energy_standby = currSD * d_f['input_voltage'].values * d_f['diff time'].values/3600. # Wh instead of kJ
    Ah_standby = np.round(Ah_standby.cumsum(),2)
    energy_standby = np.round(energy_standby.cumsum(),2)
    d_f['energy_standby'] = energy_standby * -1.
    d_f['Ah_standby'] = Ah_standby * -1.
    """AhSD, energySD = [],[]
    for ix in hi:
        energySD.append(currSD * d_f['BatteryVoltage'].values[ix] * d_f['diff time'].values[ix]/1000.)
        AhSD.append(currSD * d_f['diff time'].values[ix]/3600.)
    for i,ix in enumerate(hi):
        Ah_drain[ix:] += AhSD[i]
        energy_drain[ix:] += energySD[i]"""
    d_f['Energy drained in kJ'] = d_f['Energy RPi'] + d_f['energy_standby']
    d_f['Ah drained'] = d_f['Ah_standby'] + d_f['Ah RPi']
    datalist = []
    for ele in d_f['input_voltage'].values.tolist():
        datalist.append(voltage2energy(ele)) # act_energy,act_capacity,act_energy100,act_capacity100
    d_f['est energy'] = [x[0] for x in datalist]
    d_f['est capacity'] = [x[1] for x in datalist]
    d_f['est energy%'] = [x[2] for x in datalist]
    d_f['est capacity%'] = [x[3] for x in datalist]
    data0 = voltage2energy(d_f['input_voltage'].iloc[0])
    d_f['calc energy without gain'] = data0[0] + d_f['Energy drained in kJ'].values 
    d_f['calc capacity without gain'] = data0[1] + d_f['Ah drained'].values 
    d_f['gained energy'] = d_f['est energy'].values - d_f['calc energy without gain'].values 
    d_f['gained capacity'] = d_f['est capacity'].values - d_f['calc capacity without gain'].values
    d_f.to_csv(save_path + 'monitorAll.csv', index=False)
    config["Battery_Capacity"]=d_f['est capacity%'].iloc[-1]; config["Battery_Energy"]=d_f['est energy%'].iloc[-1]
    config["RPI_Power"]=d_f['Power Consumption'].iloc[-1]; config["Gained_Energy"]=d_f['gained energy'].iloc[-1]
    config["Gained_Capacity"]=d_f['gained capacity'].iloc[-1]; config["starttime_analyze"]=float(df['timestamp'].iloc[0])
    config["last_analyze"]=time.time() #float(df['timestamp'].iloc[-1])
    saveDict(config,filename=save_path+'config.json')
    energy_col = ['Energy drained in kJ', 'Energy solar','Energy RPi','energy_standby','est energy','calc energy without gain','gained energy']
    capacity_col = ['Ah drained','est capacity','Ah RPi','Ah_standby','calc capacity without gain','gained capacity','Ah solar']
    show(d_f,filename=save_path + 'energy.png',col2sel=energy_col)
    show(d_f,filename=save_path + 'capacity.png',col2sel=capacity_col)
    show(d_f,filename = save_path+'solar.png',col2sel =['Solar Power'])
    return d_f


def getChannelTimelineInstantWriteMinuteThread(getmean=True):
    """Get values at certain timestamps like: minute: 0,5,10...
    timeinterval: in minutes"""
    global config
    out = calcNextStartupShutdownTimeAndDelta()
    for k,v in out.items():
        if "startup" in k: config["next startup"][k] = v
        if "shutdown" in k: config["next shutdown"][k] = v
    saveDict(config,filename=save_path+'config.json')
    timeinterval = config["monitor time interval"]
    now = dt.datetime.now()
    filename = save_path + 'monitor__' + dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    logging.info('saving data under :%s', filename)
    if timeinterval < 1: timeinterval = 1
    if timeinterval > 30: timeinterval = 30
    data=['date time','time delta']
    wittypi_keys = ['DateTime','timestamp','output_voltage','input_voltage','outputcurrent','temperature']
    #data = data + ['temp' ,'humi','spikes','cpu_temp','gpu_temp','cpu_load','arm', 'core', 'h264', 'isp', 'v3d']
    data = data + ['cpu_temp','gpu_temp','cpu_load', 'brightness'] + wittypi_keys
    logging.info('header:%s',str(data))
    data = [data]
    saveCSV(csvfile=filename,datalist=data)
    starttime = time.time()
    while config["monitor"]:
        now = dt.datetime.now()
        delta_min = now.minute % timeinterval # minutes left since last record timestamp
        if delta_min == 0: 
            #print('record now and sleep for ',timeinterval, ' minutes')
            logging.info('record now and sleep for %d minutes',timeinterval)
            timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = [timestamp, round(time.time()-starttime,2)]
            cpu_gpu_temp = getRPiTemp(); config["CPU_Temp"] = cpu_gpu_temp[0]
            cpu_load = getCPUload(); config["CPU_load"] = cpu_load
            witty_pi = getAll(); config["RPi_Temp"] = witty_pi['temperature']; config["Battery_Volt"] = witty_pi['input_voltage']
            config["last_measured"] = witty_pi['timestamp']
            wittypi_val = [witty_pi[x] for x in wittypi_keys]
            brightness = getBrightness()[1]
            new_row = new_row + cpu_gpu_temp + [cpu_load] + [brightness] + wittypi_val
            #data.append(new_row)
            saveCSVappend(csvfile=filename,datalist=[new_row])
            #writer.writerow(new_row)
            #print(new_row)
            logging.info('new data %s',str(new_row))
            time.sleep(3) # wait for writing of data
            #if now.minute % config["analyze interval"] == 0: 
            #if (time.time() - config["last_analyze"] > 60.*config["analyze interval"]) and (time.time() - starttime > 60.*config["analyze interval"]) :
            if (time.time() - config["last_analyze"] > 60.*config["analyze interval"]) and (time.time() - starttime > 60. * (timeinterval+1)) :  #wait a while after restart before analyzing
                logging.info('time to analyze data')
                monitor()
                if config["send_report"]: 
                    image_list = ['battery.png','capacity.png','energy.png','solar.png']
                    image_list = [save_path + x for x in image_list]
                    for ele in image_list: telegram_send_file(ele)
            now = dt.datetime.now() # new time after measure
            #seconds2shutdown = getTotalSeconds(config["next shutdown"]['shutdown_time delta str']) 
            out = calcNextStartupShutdownTimeAndDelta()
            seconds2shutdown = getTotalSeconds(out['shutdown_time delta str']) 
            logging.info('time to shutdown %d seconds',seconds2shutdown)
            #if seconds2shutdown < (timeinterval + 1)*60:
            if seconds2shutdown < (timeinterval * 60):
                logging.info('time to shutdown %d seconds',seconds2shutdown)
                logging.info('exit python')
                time.sleep(10)
                sys.exit()
        else: print('sleep for ',delta_min, ' minutes')
        time2sleep = (timeinterval - delta_min) * 60 - now.second
        #print('sleep for ',time2sleep, ' seconds')
        logging.info('sleep for %d seconds',time2sleep)
        time.sleep(time2sleep)


### init 

config = loadDict(filename=save_path+'config.json')

for ele in ['start_time',"starttime_analyze"]:
    config[ele] = time.time()


# logging ###########################################################################
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(levelname)s:%(name)s: %(message)s '
                    '(%(asctime)s; %(filename)s:%(lineno)d)',
            'datefmt': "%Y-%m-%d %H:%M:%S",
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO', #'DEBUG',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'rotate_file': {
            'level': 'INFO', #'DEBUG',
            'formatter': 'standard',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': save_path + 'monitor.log',
            'encoding': 'utf8',
            'maxBytes': 100000,
            'backupCount': 1,
        }
    },
    'loggers': {
        '': {
            'handlers': ['console', 'rotate_file'],
            'level': 'DEBUG',
        },
    }
}
logging.captureWarnings(False) #send warnings to log

logging.config.dictConfig(LOGGING)


logging.info('Brightness %d',getBrightness()[1])

battVolt = np.load(save_path+"BatteryVoltage.npy")
energy = np.load(save_path+"EnergyLeft.npy") * config["BatteryFactor"]/3.6 # absolute values, / 3.6 kJ -> Wh
capacity = np.load(save_path+"Capacity.npy") * config["BatteryFactor"] # absolute values
energy100 = np.load(save_path+"EnergyLeft100.npy") # in procent
capacity100 = np.load(save_path+"Capacity100.npy") # in procent

####

# save_path= '/home/pi/Documents/MonitorStationRpi4two/'  energy = np.load(save_path+"EnergyLeft.npy")/3.6
#np.save(save_path+"BatteryVoltage", battVolt)
#np.save(save_path+"EnergyLeft", energy)
#np.save(save_path+"Capacity", capacity)
#np.save(save_path+"EnergyLeft100", energy100)
#np.save(save_path+"Capacity100", capacity100)

#battery = {'date time': None, 'DateTime': None,'energy': None, 'capacity': None, 'energy%': None, 'capacity%': None}

"""

fig, ax = plt.subplots()
ax.scatter(battVolt[25:-30],capacity[25:-30],alpha=0.4)
ax.set_xlabel('Battery Voltage in V', fontsize=14)
ax.set_ylabel('Battery Capacity in Ah', fontsize=14)
ax.set_title('Experiment: Battery Capacity by Battery Voltage',fontsize=16)
ax.grid(True)
fig.tight_layout();plt.show()

fig, ax = plt.subplots()
ax.scatter(battVolt[25:-30],energy[25:-30],alpha=0.4)
ax.set_xlabel('Battery Voltage in V', fontsize=14)
ax.set_ylabel('Battery Energy in Wh', fontsize=14)
ax.set_title('Experiment: Battery Energy by Battery Voltage',fontsize=16)
ax.grid(True)
fig.tight_layout();plt.show()



"""












if __name__ == "__main__":
    monitor_thread = Thread(name='monitor_thread', target=getChannelTimelineInstantWriteMinuteThread, kwargs={'getmean': True})
    monitor_thread.daemon = True
    monitor_thread.start()
    bot = telegram.Bot(token=config['telegram_bot_token'])
    #telegram_thread = Thread(name='telegram_thread', target=telegram_bot, kwargs={'token': config['telegram_bot_token']})
    #telegram_thread.daemon = True
    #telegram_thread.start()
    try:
        logging.info("start monitor thread")
        telegram_send_message('monitor station is running')
        telegram_bot(token=config['telegram_bot_token'])
        while 1:
            time.sleep(100)
    except KeyboardInterrupt:
        sys.exit()





