FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh
RUN groupadd --gid 10001 biolog \
    && useradd --uid 10001 --gid biolog --create-home biolog \
    && mkdir -p /data \
    && chown -R biolog:biolog /app /data /home/biolog

USER biolog
ENTRYPOINT ["./entrypoint.sh"]
