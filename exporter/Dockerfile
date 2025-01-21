FROM python:3.8-slim

WORKDIR /app

# Copy the necessary files into the container
COPY smoketest.py /app/smoketest.py
COPY config.json /app/config.json
COPY requirements.txt /app/requirements.txt 

# Install dependencies
RUN pip install -r requirements.txt  

RUN apt-get update
RUN apt-get install iputils-ping -y

EXPOSE 9111

# Set the default command to run the smoketest.py script
CMD ["python", "smoketest.py", "-c", "/app/config.json", "-f", "/app/l.log"]