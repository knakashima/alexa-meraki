from __future__ import print_function
# ^ this provides support for Python 3.x style printing

"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

"""
First, we will import a handful of libraries to use their pre-written
functions and save some lines of code. If you need to import external
libraries (libraries not baked into AWS Lambda by default), then you will need
to create a deployment package and upload it to Lambda vs. being able to use
the Lambda in-line code editor. Some info about that has been included in the
guide shared with this example
"""

import pysnmp
from pysnmp.entity.rfc3413.oneliner import cmdgen
# snmp_helper courtesy Kirk Byers: https://github.com/ktbyers/pynet/blob/master/snmp/snmp_helper.py
import snmp_helper
import requests
import json
import meraki_info

"""
Pulling in info from meraki_info.py (a local file in the same directory as this
script) and assigning to variables used later in the script. This lets us omit
private info from this file, so it can be shared easily without needing to
first scrub personal bits of info (like your API key, Org ID, etc...)

meraki_info.py is basically just a text file with this snippet for example:
...
api_key = '<the actual API key>'
my_org_id = '<the org id you are using in this script>'
snmp_port = 16100
...
"""
# Global variables used in the script
api_key = meraki_info.api_key
my_org_id = meraki_info.org_id
net_id = meraki_info.net_id
base_url = meraki_info.base_url
org_url = meraki_info.org_url
bind_url = meraki_info.bind_url
unbind_url = meraki_info.unbind_url
template_data = json.dumps(meraki_info.template_data)
community_string = meraki_info.community_string
snmp_port = meraki_info.snmp_port
headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}


# --------------- Alexa provided functions ------------------
""" This section is almost entirely copy & paste from a baseline skill sample.
The only lines added are rows 111-120 based on 'intents' defined for this
skill at developer.amazon.com (under the Alexa section where the skill itself
is defined).
"""

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment the below if statement and populate with your skill's unique
    application ID to prevent someone else from sending requests to this
    function and potentially running up your AWS charges =)
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])


def on_session_started(session_started_request, session):
    """ Called when the session starts """
    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """
    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """
    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    """ Dispatch to your skill's intent handlers based on the 'intent_name'
    the Alexa service sends over. Example: If Alexa sends over an 'intent_name'
    of "GetStatus", that will call the 'get_network_status' function defined
    below.
    """
    if intent_name == "GetStatus":
        return get_network_status()
    elif intent_name == "GetRoadmap":
        return get_roadmap()
    elif intent_name == "GetInventory":
        return get_inventory()
    elif intent_name == "CloseShop":
        return close_shop()
    elif intent_name == "OpenShop":
        return open_shop()
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.
    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Alexa functions that control the skill's behavior ------------------


""" On to the fun stuff... The 'get_welcome_response' function below
is called when you say, "Alexa, ask <my custom skill name>." If you do not
include an intent, the 'get_welcome_response' function is called. The custom
skill name is defined at developer.amazon.com under the Alexa section.

The 'speech_output' variable is what Alexa ultimately responds with.
"""
def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """
    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to the Alexa Meraki Application. " \
                    "You can ask me for network status, inventory, " \
                    "and to open or close this shop. "
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Please ask me to do something like, " \
                    "what is the network status?"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


# --------------- Helper functions from Georg Prause & Rob Watt  ------------------


# Get info from the organization
def get_orginfo():
    """
    Some functions may seem redundant for this basic example, but have been
    included for reference. You can find many of these pre-built functions
    in Rob Watt's provisioning API library for more examples:
    https://github.com/meraki/provisioning-lib

    Anytime you see 'requests' called, the same API call can be done in
    Postman to follow along. For the example below, 'org_url' is defined as
    meraki_info.org_url on row 44 above. If we look at the meraki_info.py
    file (imported on line 28), here are the relevant lines:
    ...
    org_id = '123456' (123456 as an example org ID)
    base_url = 'https://dashboard.meraki.com/api/v0/'
    org_url = '{0}/organizations/{1}'.format(str(base_url), str(org_id))
    ...

    This means 'org_url'effectively becomes:
    https://dashboard.meraki.com/api/v0/organizations/123456

    This URL could be used in Postman to run a GET against to examine the
    output.
    """
    orgs = requests.get(org_url, headers=headers).text
    result = json.loads(orgs)
    return result


# Get the org-name of a specific org-id
def get_orgname(org_info):
    """
    This function takes the output of 'get_orginfo' above and iterates through
    each "k, v" (user defined btw / "k, v" could easily be "var1, var2" for
    example). When a key ("k") called 'name' is found, the value ("v") is
    assigned to a variable called "org_name" (user defined again) and returned
    as the output of this function.
    """
    for k, v in org_info.iteritems():
        org_name = org_info['name']
    return org_name


# Get inventory and store models and their count in a dictionary
def get_orginv():
    """
    This function uses requests to GET the org inventory, counts the model
    types, and writes them to a dictionary called org_inventory.
    """
    # creates the dictionary called org_inventory to store key,value pairs
    org_inventory = {}
    # appending '/inventory' to 'org_url' and calling the new URL 'inv_url'
    inv_url = org_url + '/inventory'
    inventory = requests.get(inv_url, headers=headers).text
    result = json.loads(inventory)
    for row in result:
        if row == 'errors':
            return 'errors'
        else:
            # iterate through the json response from the GET inventory
            for key, value in row.iteritems():
                """
                When "key" is 'model', if the 'value' of model (example
                'MX65') does not already exist in 'org_inventory', set 'MX65'
                as the key and assign a value of 1 (first one). If that model
                already exists in 'org_inventory', then +1 the count each time
                we see the same model as we iterate through each row of the
                result above.
                """
                if key == 'model':
                    if not value in org_inventory:
                        org_inventory[value] = 1
                    else:
                        org_inventory[value] += 1
    return org_inventory


# --------------- Meraki custom functions ------------------


# Get the devName and devStatus SNMP OIDs
def get_network_status():
    """ Grabs network status (via SNMP for now) and creates the 'speech_output'
    """
    session_attributes = {}
    card_title = "Network Status"
    # creating a few lists to write things to
    keys = []
    values = []
    list_offline = []
    # community_string and snmp_port are set above on lines 52 & 53 under the
    # global variables section
    device = ('snmp.meraki.com', community_string, snmp_port)
    # snmp_data1 is the list of devNames in the SNMP get response
    # snmp_helper is imported on line 25, see snmp_helper.py in the example
    snmp_data1 = snmp_helper.snmp_get_oid(device, oid='.1.3.6.1.4.1.29671.1.1.4.1.2', display_errors=True)
    # snmp_data2 is the 0 or 1 value that comes back from this OID indicating
    # the device's online/offline status (0 = offline, 1 = online)
    snmp_data2 = snmp_helper.snmp_get_oid(device, oid='.1.3.6.1.4.1.29671.1.1.4.1.3', display_errors=True)

    """
    Create a dictionary of device names and their online/offline status.
    snmp_extract comes from the import of snmp_helper on line 25 for reference.
    The following lines clean up the SNMP responses in snmp_data1 and
    snmp_data2 individually, then add the sanitized data points to
    dict_status (SNMP 'devName' and '0' or '1' for the status)
    """
    for i in snmp_data1:
        k = snmp_helper.snmp_extract(i)
        keys.append(k)
    for j in snmp_data2:
        m = snmp_helper.snmp_extract(j)
        values.append(m)
    # Create a new dictionary 'dict_status' with the combined name and status
    dict_status = dict(zip(keys, values))
    # Now iterate through dict_status to capture offline devices
    for key in dict_status:
        value = dict_status[key]
        if value == '0':
            # below, 'devName' of offline devices (devStatus = 0) is appended
            # to list_offline (row 266)
            list_offline.append(key)
        else:
            # skip over devices which are not offline (any value other than 0)
            continue
    # Finally, count the length of 'list_offline' to get the number of offline
    # devices and read back each name in the list.
    # The extra spaces around the comma help Alexa read the names back clearly.
    # Adjustments may need to be made to fine tune the response.
    speech_output = "%s devices are offline, %s. would you like me to dispatch a technician ?" % \
                    (str(len(list_offline)), " , ".join(list_offline))
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_inventory():
    """ Grabs inventory and creates a reply for the user
    """
    session_attributes = {}
    card_title = "Inventory"

    # Store the list of organizations in org_info
    org_info = get_orginfo()
    # Create a new list of model names and their count in inventory
    speech_list = []
    # get_orgname() is defined starting on line 207
    org_name = get_orgname(org_info)
    # get_orginv() is defined starting on line 221
    inv = get_orginv()
    # Loop through the inventory and create a list of device models and their
    # respective count to use in 'speech_output'
    for k, v in inv.iteritems():
        model_name = k
        dev_count = v
        txt1 = "%s , %s" % (model_name, dev_count)
        speech_list.append(str(txt1))
    speech_output = "%s - device inventory, %s" % (org_name, speech_list)
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def close_shop():
    """ Binds an existing template with the Guest SSID disabled. Additional
    smart home functions could easily be added to turn off lights, lock doors,
    set a security alarm, set an away thermostat setting for example...
    """
    session_attributes = {}
    card_title = "Close the shop"
    bind = requests.post(bind_url, headers=headers, data=template_data)
    if bind.status_code == 200:
        speech_output = "Success ! Disabling guest wi-fi"
    else:
        speech_output = "Unsuccessful"
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def open_shop():
    """ Unbinds an existing template (see note above for other ideas)...
    """
    session_attributes = {}
    card_title = "Open the shop"
    unbind = requests.post(unbind_url, headers=headers)
    if unbind.status_code == 200:
        speech_output = "Success ! Enabling guest wi-fi"
    else:
        speech_output = "Unsuccessful"
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_roadmap():
    """ A silly easter egg for Merakians =)
    """
    session_attributes = {}
    card_title = "roadmap"
    speech_output = "The first rule of Meraki roadmaps, " \
                    "is we do not talk about Meraki roadmaps. "
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


# --------------- Helpers that build all of the responses ----------------------


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': 'SessionSpeechlet - ' + title,
            'content': 'SessionSpeechlet - ' + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }
