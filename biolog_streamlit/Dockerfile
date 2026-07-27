FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --gid 10001 biolog \
    && useradd --uid 10001 --gid biolog --create-home biolog \
    && chown -R biolog:biolog /app /home/biolog

USER biolog
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
