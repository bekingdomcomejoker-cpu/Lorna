FROM python:3.12-slim
WORKDIR /app
COPY . /app
ENV CAT_EOF_HOME=/data/cat_eof
ENV ALETHEIA_HOST=0.0.0.0
ENV ALETHEIA_PORT=8765
RUN mkdir -p /data/cat_eof
EXPOSE 8765
CMD ["python3","-m","federation.server"]
