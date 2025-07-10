FROM python:3.11-slim

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
    apt-get install -y curl && \
    curl -sfL https://raw.githubusercontent.com/reviewdog/reviewdog/master/install.sh | sh -s -- -b /usr/local/bin

COPY src/ /action
COPY entrypoint.sh /action
WORKDIR /action
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]