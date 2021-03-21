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

driver = ''
counter = 0
minwait = 90
maxwait = 120
found_counter = 0

def watchZipCode(zips, notifications, smtp_config):
    global driver
    global counter
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

        for zipCode in zips:
            logging.info(f"Searching for zipCode: {zipCode}")
            if counter > 60:
                raise Exception("Too many retries, quitting")
            driver.get("https://www.walgreens.com/findcare/vaccination/covid-19/location-screening")
            try:
                element = driver.find_element_by_id("inputLocation")
            except NoSuchElementException:
                logging.info(f"Could not find inputLocation element")
                logging.info(driver.page_source.encode("utf-8"))
                counter = counter + 1
                time.sleep(random.randrange(minwait, maxwait))
                continue
            element.clear()
            element.send_keys(zipCode)
            logging.info(f"Sent zipcode: {zipCode}")
            try:
                button = driver.find_element_by_css_selector("button.btn")
            except NoSuchElementException:
                logging.info(f"Could not find button.btn element")
                counter = counter + 1
                time.sleep(random.randrange(minwait, maxwait ))
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
                if found_counter >= 2:
                    logging.info("Found twice in a row, sending message")
                    sendText(notifications, smtp_config, message)
                    hasBeenSeen[zipCode] = True
            elif not aptFound:
                logging.info(f"No Appointments for zipcode {zipCode}")
                found_counter = 0
                hasBeenSeen[zipCode] = False

        time.sleep(random.randrange(minwait, maxwait))


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
    try:
        watchZipCode(
            config['zipcodes'],
            config['notifications'],
            config['smtp_config']
        )
    except Exception as e:
        driver.quit()
        raise e
