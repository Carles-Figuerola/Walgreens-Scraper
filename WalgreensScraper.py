from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import smtplib
import random
import json
import sys
import logging

# Shared variables
driver = None
error_counter = 0
found_counter = 0

# Configurable settings
minwait = 90
maxwait = 120
max_found_counter = 5
foundwait = 60
errorwait = 600
max_errors = 4

def watchZipCode(zips, notifications, smtp_config):
    global driver
    global error_counter
    global found_counter
    
    hasBeenSeen = {}
    for zipCode in zips:
        hasBeenSeen[zipCode] = False

    chromeOptions = webdriver.ChromeOptions()
    chromeOptions.add_argument("--no-sandbox") 
    chromeOptions.add_argument("--headless") 
    chromeOptions.add_argument("--disable-setuid-sandbox") 
    chromeOptions.add_argument("--remote-debugging-port=9222")  # this
    chromeOptions.add_argument("--disable-dev-shm-using") 
    chromeOptions.add_argument("--disable-extensions") 
    chromeOptions.add_argument("--disable-gpu") 
    driver = webdriver.Chrome(options=chromeOptions)

    driver.get("https://www.walgreens.com/findcare/vaccination/covid-19")
    btn = driver.find_element_by_css_selector('span.btn.btn__blue')
    btn.click()
    driver.get("https://www.walgreens.com/findcare/vaccination/covid-19/location-screening")
    while True:

        if found_counter > 0:
            wait_time = foundwait
        else:
            wait_time = random.randrange(minwait, maxwait)

        if error_counter > 0:
            logging.warning(f"We think we got banned, waiting {errorwait} to back off")
            time.sleep(errorwait)
            continue

        if error_counter > max_errors:
            raise Exception("Too many retries, quitting")

        for zipCode in zips:
            logging.info(f"Searching for zipCode: {zipCode}")
            driver.get("https://www.walgreens.com/findcare/vaccination/covid-19/location-screening")
            try:
                element = driver.find_element_by_id("inputLocation")
            except NoSuchElementException:
                logging.error(f"Could not find inputLocation element")
                logging.error(driver.page_source.encode("utf-8"))
                error_counter = error_counter + 1
                time.sleep(wait_time)
                continue
            element.clear()
            element.send_keys(zipCode)
            try:
                button = driver.find_element_by_css_selector("button.btn")
            except NoSuchElementException:
                logging.error(f"Could not find button.btn element")
                error_counter = error_counter + 1
                time.sleep(wait_time)
                continue
            button.click()
            time.sleep(0.75)
            alertElement = getAlertElement(driver)
            aptFound = alertElement.text == "Appointments available!"

            if aptFound and not hasBeenSeen[zipCode]:
                logging.info("======================APPOINTMENT FOUND! ZIP CODE: "+zipCode+"======================")
                message = "APPOINTMENT FOUND! ZIP CODE: "+zipCode
                found_counter = found_counter + 1
                logging.info(f"Found {found_counter} times")
                if found_counter >= max_found_counter:
                    logging.info("Found twice in a row, sending message")
                    sendText(notifications, smtp_config, message)
                    hasBeenSeen[zipCode] = True
            elif not aptFound:
                logging.info(f"No Appointments for zipcode {zipCode}")
                found_counter = 0
                hasBeenSeen[zipCode] = False

        time.sleep(wait_time)


def getAlertElement(driver):
    while True:
        try:
            alertElement = driver.find_element_by_css_selector("p.fs16")
            return alertElement
        except NoSuchElementException:
            time.sleep(0.5)


def sendText(notifications, smtp_config, message):
    Subject = 'Subject: Covid Vaccine:\n\n'

    # Login to SMTP
    if smtp_config['port'] == 587:
        conn = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
        conn.ehlo()
        conn.starttls()
    elif smt_config['port'] == 465:
        conn = smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port'])
    else:
        logging.error("Do not know how to use this smtp server")
        exit(1)
    conn.login(smtp_config['username'], smtp_config['password'])

    # Send a text
    if 'number' in notifications and 'carrier' not in notifications:
        logging.error("You need to specify a carrier")
        exit(1)
    if 'number' in notifications and 'carrier' in notifications:
        carriers = {
            'att': '@mms.att.net',
            'tmobile': ' @tmomail.net',
            'verizon': '@vtext.com',
            'sprint': '@page.nextel.com'
        }
        to_number = notifications['number']+'{}'.format(carriers[notifications['carrier']])
        conn.sendmail(smtp_config['sender'], to_number, Subject + message)

    # Send an email
    if 'email' in notifications:
        conn.sendmail(smtp_config['sender'], notifications['email'], Subject + message)

    # Close
    conn.quit()

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    if len(sys.argv) < 2:
        logging.error("Put a json config file as a parameter")
        exit(1)
    with open(sys.argv[1], 'r') as fd:
        config = json.load(fd)
    if 'settings' in config:
        if 'minwait' in config['settings']:
            minwait = config['settings']['minwait']
        if 'maxwait' in config['settings']:
            maxwait = config['settings']['maxwait']
        if 'max_found_counter' in config['settings']:
            max_found_counter = config['settings']['max_found_counter']
        if 'foundwait' in config['settings']:
            foundwait = config['settings']['foundwait']
        if 'errorwait' in config['settings']:
            errorwait = config['settings']['errorwait']
        if 'max_errors' in config['settings']:
            max_errors = config['settings']['max_errors']
    try:
        watchZipCode(
            config['zipcodes'],
            config['notifications'],
            config['smtp_config']
        )
    except Exception as e:
        driver.quit()
        raise e
