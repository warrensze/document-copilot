```dockerfile
FROM python:3.12-slim
RUN pip install opencode && \
    adduser --disabled-password --gecos '' sandbox
USER sandbox
WORKDIR /workspace
