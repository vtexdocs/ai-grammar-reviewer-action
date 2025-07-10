FROM python:3.11-slim

WORKDIR /github/workspace

COPY src/ .
COPY entrypoint.sh .

RUN pip install --no-cache-dir -r requirements.txt

# Install reviewdog
RUN apt-get update && \
    apt-get install -y curl && \
    curl -sfL https://raw.githubusercontent.com/reviewdog/reviewdog/master/install.sh | sh -s -- -b /usr/local/bin

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]