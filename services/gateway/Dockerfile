FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src /app/src
ENV PYTHONPATH=/app/src
EXPOSE 8000
CMD ["python","-m","elevator_gateway"]
