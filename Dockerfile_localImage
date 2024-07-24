# app/Dockerfile

FROM python:3.9-slim

WORKDIR /translator_playground

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY testApp.py .
COPY requirements.txt .
COPY tmxFileProcess.py .
COPY bedrock_apis.py .

COPY requirements.txt /tmp/
RUN pip3 install --requirement /tmp/requirements.txt
COPY . /tmp/

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "testApp.py", "--server.port=8501", "--server.address=0.0.0.0"]