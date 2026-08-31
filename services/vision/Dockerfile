FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements/base.txt /app/requirements/base.txt
RUN pip install --no-cache-dir -r /app/requirements/base.txt
COPY src /app/src
COPY database /app/database
ENV PYTHONPATH=/app/src CV_BACKEND=mock CAMERA_SOURCE=mock CV_DB_ENABLED=false
EXPOSE 8010
CMD ["python", "-m", "elevator_vision"]
