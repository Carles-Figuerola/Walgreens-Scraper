FROM ubuntu:20.04

# Install tools
RUN apt-get update && apt-get install -y wget gnupg2 unzip curl python3-pip

# install google chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y google-chrome-stable

# install chromedriver
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# set display port to avoid crash
ENV DISPLAY=:99

# Install project requirements
COPY requirements.txt /
RUN pip3 install --no-cache -r requirements.txt

COPY WalgreensScraper.py /
ENTRYPOINT ["python3", "/WalgreensScraper.py", "/config.json"]
