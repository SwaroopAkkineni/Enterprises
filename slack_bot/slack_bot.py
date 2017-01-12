#!/usr/bin/env python

from slackclient import SlackClient
import time, json, sys, re, os
import RPi.GPIO as GPIO

token=os.environ.get('SLACK_TOKEN')

bot_userid="U3FFGJ8S1"
command_prefix=":botface"
TRIG_PORT=27

sc=SlackClient(token)

# Test API
res=sc.api_call("api.test")
sys.stdout.write("Test:\n")
sys.stdout.write(str(res)+"\n")
sys.stdout.write("(completed)\n\n")


user_dir={}
keyw_dur_map={}

keyw_dur_map["activate"]=4

###############################################################################

def execute_gpio(port, dur):

	sys.stdout.write("Triggering: Port: "+str(port)+" for "+ str(dur)+" sec(s)\n")
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(port, GPIO.OUT)
	GPIO.output(port, GPIO.HIGH)
	time.sleep(dur)
	GPIO.output(port, GPIO.LOW)

	return

#------------------------------------------------------------------------------

def scan_message(message, user):

	# Look for something like:
	# :botface add 4
	# If command not found, then search for keywords

	print(message)	
	message=message.lower()

	regex_str="^" + command_prefix
	regex=re.compile(regex_str)
	result=regex.match(message)

	if(result!=None):
		# COMMAND

		result=re.split(" ", message)
		res_len=len(result)

		try:
			cmd=result[1];
			keyword=result[2];
			dur=result[3];
		except IndexError:
			pass

		if(res_len==4 and cmd=="add"):
			try:
				dur_val=float(dur)
				keyw_dur_map[keyword]=dur_val
				reply = "'"+keyword + "' added with " + dur + " as response."
			except ValueError:
				reply = "Could not convert: " + dur + " to a number."
				
		elif(res_len==3 and cmd=="rem"):
			try:
				del keyw_dur_map[keyword]
				reply="ok. '" + keyword + "' deleted."
			except KeyError:
				reply="Keyword not found."

		elif(res_len==2 and cmd=="lis"):
			reply=keyw_dur_map

		elif(res_len==2 and cmd=="say_my_name"):
			reply="yes, " + user + "!!"

		else:
			reply="no entiendo your command, yo..."
		return reply
	else:
		#reply="[[" + message + "]]"
		# Search keywords

		for key in keyw_dur_map:
			found=re.search(key, message)
			if(not found==None):
				execute_gpio(TRIG_PORT, keyw_dur_map[key])
		reply=None
	
	return reply

#------------------------------------------------------------------------------

def get_user_name(user_id):
	try:
		user_name=user_dir[user_id]
	except KeyError:
		sys.stdout.write("Asking for user info.\n")
		ui_re=sc.api_call("users.info", user=user_id)
		user_dir[user_id]=ui_re["user"]["name"]
		sys.stdout.write("Added: "+user_dir[user_id]+" to cache.\n")
		user_name=user_dir[user_id]
	return(user_name)

###############################################################################

# Get identity
sys.stdout.write("Acquiring my own identity...\n")
res=sc.api_call("auth.test")
sys.stdout.write(str(res)+"\n")
bot_userid=res["user_id"]
bot_name=get_user_name(bot_userid)
sys.stdout.write("I am: "+bot_userid+" / "+bot_name+"\n\n")

# Start main loop	
sys.stdout.write("\n\nConnecting...\n")
if sc.rtm_connect():

	sys.stdout.write("Connected.  Listening...\n")
	while True:
		msg=sc.rtm_read()
		if(len(msg)==0):
			sys.stdout.write('.')
			sys.stdout.flush()
		else:
			try:
				sys.stdout.write("\n")
				for evt in msg:
					print(evt)

					if(evt["type"]=="message"):
						try:
							if(evt["subtype"]=="message_changed"):
								user=evt["message"]["user"]
								text=evt["message"]["text"]
							if(evt["subtype"]=="message_deleted"):
								sys.stdout.write("Message Deleted...\n")
								continue
						except:
							user=evt["user"]
							text=evt["text"]

						user_name=get_user_name(user)

						if(user==bot_userid):
							sys.stdout.write("(Ignoring message from self.)\n")
							# Ignore message from self
						else:
							reply=scan_message(text, user_name)
					
							if(not reply==None):
								sc.api_call("chat.postMessage", channel=evt["channel"], 
								text=reply, as_user=True)

					elif(evt["type"]=="presence_change"):
						user_name=get_user_name(evt["user"])
						presence=evt["presence"]
						
						sys.stdout.write(user_name + " went " + presence + "\n")

			except Exception as e:
				sys.stdout.write("****************************************************\n")
				sys.stdout.write("Unhandled Exception:\n")
				sys.stdout.write(str(e))
				sys.stdout.write("\n****************************************************\n")
		time.sleep(1)
else:
	print("Connection Failed, invalid token?")

