# app/Dockerfile

FROM public.ecr.aws/docker/library/python:3.9-slim

WORKDIR /translator_playground


COPY main.py .
COPY requirements.txt .
COPY tmxFileProcess.py .
COPY bedrock_apis.py .

COPY requirements.txt /tmp/
RUN pip3 install --requirement /tmp/requirements.txt


EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]