FROM python:3.13-slim
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Set a working directory
WORKDIR /app

# Copy files into place
COPY mqtt2mqtt.py dutycycle.py requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "mqtt2mqtt.py"]

