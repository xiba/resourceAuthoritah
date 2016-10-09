FROM alpine:3.3

# Update
RUN apk add --no-cache redis python3 py-redis py-flask py-pip

# Bundle app source
COPY flaskApp.py /src/flaskApp.py
COPY resourceInterface.py /src/resourceInterface.py
COPY testFlaskApp.py /src/testFlaskApp.py

EXPOSE  8000
CMD ["python", "/src/flaskApp.py", "-p 8000"]
