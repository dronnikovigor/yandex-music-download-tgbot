FROM python:3.10-slim
RUN apt-get update && apt-get install -y \
    git

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME /app/downloads

CMD ["python", "main.py"]