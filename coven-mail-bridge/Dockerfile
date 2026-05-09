FROM python:3.12-slim
WORKDIR /app
COPY server.py .
EXPOSE 18793
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:18793/health', timeout=2)"
CMD ["python", "-u", "server.py"]
