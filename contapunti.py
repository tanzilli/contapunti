# (C) 2018 Sergio Tanzilli <tanzilli@acmesystems.it>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import paho.mqtt.publish as publish
from crono import Crono
from acmepins import GPIO,PWM
import time
import thread
import threading
from bot import Bot

#@TabelloneBot
telegram_bot=Bot("place your telegram token here")

# PWM a 38KHz per led IR
led_ir_out = PWM("J4.34",38000)    

# Imposta il duty cycle al 50%
led_ir_out.start(50)
 
crono=Crono()
blue_score=0
red_score=0
last_score="none"

#Controllo di chi ha vinto
def scores_check(blue_score,red_score,crono):
	if abs(blue_score-red_score)>=2 and blue_score>=10 and blue_score>red_score:
		print "blue wins" 
		crono.stop()
		return "blue"
	if abs(blue_score-red_score)>=2 and red_score>=10 and red_score>blue_score:
		print "red wins" 
		crono.stop()
		return "red"
	return "none"

#Gestione lampeggio led spia	
def blink(gpio,times=1,delay=0.5):
	for i in range(times):
		gpio.on()
		time.sleep(delay)
		gpio.off()
		time.sleep(delay)

#Update MQTT scores

def update_mqtt_scores(blue_score,red_score):
	publish.single("bluescore", "%d" % blue_score, hostname="videowall.local")
	publish.single("redscore", "%d" % red_score, hostname="videowall.local")

#Gestione del gioco. Questa funzione viene lanciata in
#un thread separato ed esegue il loop di gestione del gioco
crono, blue_score, red_score, last_score

#GPIO usati come ingressi dai fotoaccoppiatori IR
IR_RED=GPIO("J4.36","INPUT")
IR_BLUE=GPIO("J4.38","INPUT")
IR_PULL=GPIO("J4.40","INPUT")

#Led spia interno
LED=GPIO("J4.24","LOW")

update_mqtt_scores(blue_score,red_score)

#Loop principale di gestione del gioco
while True:
	if IR_PULL.get_value()==1:
		print "Pull"
		blink(LED,1,0.2)
		counter=0
		while IR_PULL.get_value()==1:
			time.sleep(1)
			counter+=1
			#Se il tirante e' tenuto per piu' di 2 secondi resetta la partita
			if counter>=2:
				crono.reset()
				crono.start()
				blue_score=0
				red_score=0
				last_score="none"
				telegram_bot.send_alert("Inizio partita")
				print "Reset"
				
				update_mqtt_scores(blue_score,red_score)
				break
				
		#Se il tirante e' tenuto per meno di 2 secondi annulla l'ultimo goal
		if last_score=="red" and red_score>0:
			red_score-=1
			last_score="none"
			crono.start()
			telegram_bot.send_alert("Breaking news ! Annullato il goal dei rossi")
			telegram_bot.send_alert("Rossi %02d - Blue %02d" % (red_score,blue_score))
			update_mqtt_scores(blue_score,red_score)
		if last_score=="blue" and blue_score>0:
			blue_score-=1
			last_score="none"
			crono.start()
			telegram_bot.send_alert("Breaking news ! Annullato il goal dei blu")
			telegram_bot.send_alert("Blu %02d - Rossi %02d" % (blue_score,red_score))
			update_mqtt_scores(blue_score,red_score)

	#Legge gli IR delle porte solo se nessuno ha ancora vinto
	if scores_check(blue_score,red_score,crono)=="none":

		#Lettura IR porta dei rossi	
		if IR_RED.get_value()==1:
			blue_score=blue_score+1
			last_score="blue"
			print "Goal for blue %d" % blue_score
			telegram_bot.send_alert("Goal dei blu\nBlu %02d - Rossi %02d" % (blue_score,red_score))
			if scores_check(blue_score,red_score,crono)=="blue":
				telegram_bot.send_alert("Vittoria dei Blue !!\nDurata della partita: %s\nRisultato: Blu %02d - Rossi %02d" % (crono.get(),blue_score,red_score))
			blink(LED,2,0.2)
			update_mqtt_scores(blue_score,red_score)
			time.sleep(1)

		#Lettura IR porta dei blue	
		if IR_BLUE.get_value()==1:
			red_score=red_score+1
			last_score="red"
			print "Goal for red %d" % red_score
			telegram_bot.send_alert("Goal dei rossi\nRossi %02d - Blu %02d" % (red_score,blue_score))
			if scores_check(blue_score,red_score,crono)=="red":
				telegram_bot.send_alert("Vittoria dei Rossi !!\nDurata della partita: %s\nRisultato: Rossi %02d - Blu %02d" % (crono.get(),red_score,blue_score))
			blink(LED,3,0.2)
			update_mqtt_scores(blue_score,red_score)
			time.sleep(1)
