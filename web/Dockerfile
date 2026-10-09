FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade "pip>=26.2" && pip install --no-cache-dir -r requirements.txt
COPY app.py ./
ENV PORT=8080
CMD ["sh", "-c", "exec gunicorn --bind :${PORT} --workers 1 --threads 4 --timeout 60 app:app"]
