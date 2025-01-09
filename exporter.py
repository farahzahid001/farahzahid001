import subprocess
import argparse
import time
import logging
import logging.handlers
import json
from datetime import datetime
import os
import threading
from prometheus_client import start_http_server, Gauge

# Declare `my_logger` at the global level
my_logger = None

# Prometheus metrics
metric_success_duration_millisec = Gauge('metric_success_duration_millisec', 'Duration of successful tests in milliseconds', ['service'])
metric_smoketest_exporter_status = Gauge('metric_smoketest_exporter_status', 'Status of the smoketest exporter')
metric_service_success = Gauge('metric_smoketest_success', 'Service success status', ['service'])
metric_service_slowness = Gauge('metric_smoketest_slowness', 'Service slowness status', ['service'])
metric_service_duration = Gauge('metric_smoketest_duration', 'Service duration in seconds', ['service'])
metric_service_raw_message = Gauge('metric_smoketest_raw_message', 'Service raw message', ['service'])

raw_metrics = {}  # all stuff for the metrics will be stored here
running_interval = 180  # interval for running smoketests in seconds
state = 'successful'  # initial status of all the smoketests.
lock = threading.Lock()  # Thread safety lock

# config_file_path = r"/app/config.json"

# Creates formatted message about smoketest command failure reason in case of connection failure.
def create_custom_short_message(service, raw_message):
    default_message = service + ' smoketest command has been failed.'
    raw_message = raw_message.lower().strip().replace(",", "\t").replace("\n", " ")
    if 'connect' in raw_message:
        if 'refused' in raw_message or 'failed' in raw_message or 'denied' in raw_message:
            write_log('INFO', "Shortening error message for service: " + service)
            short_message = 'Smoketest command is unable to connect to service: ' + service
        else:
            short_message = default_message
    else:
        short_message = default_message
    return short_message

def write_log(level, message):
    batchtime = datetime.today().strftime('%Y-%m-%dT%H:%M:%S.%fZ')  # generating batchtime as a string
    log_message = batchtime + ' ' + level + ' ' + message.strip().replace(";", "\t") 
    if my_logger:
        my_logger.debug(log_message + '\n')
        print(log_message)
    if 'SERVICE_DEBUG' in os.environ.keys():
        if os.environ['SERVICE_DEBUG'] == 'true':
            print(log_message)

def smoketest(config, service):
    result = {
        "success": 0,
        "failures": 0,
        "slowness": 0,
        "raw_message": "",
    }
    running_interval = config['generic']['running_interval']  # interval for running smoketests in seconds

    while True:
        # setting up kinit prior smoketests.
        # user = os.environ['USER']
        # print(f"User: {user}")  # Debugging statement
        # try:
        #     subprocess.run(
        #         ['kinit', '-kt', f'/home/{user}/.keytab/{user}.keytab', f'{user}@INTRANET.BARCAPINT.COM'],
        #         stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, timeout=60)
        #     write_log('INFO', "'kinit' successful for service: " + service)
        # except subprocess.CalledProcessError as e:
        #     write_log("ERROR", "Cannot run 'kinit' for service: " + service)
        #     return

        start_time = round(time.time())
        output = None
        try:
            output = subprocess.run(
                config['services'][service]['command'], 
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                universal_newlines=True,
                timeout=config['services'][service]['timeout'],
                check=True)
            result['success'] = 1  # Success
        except subprocess.TimeoutExpired as e:
            result['slowness'] = 1  # Timed out
            result['success'] = 0  # Failure
            result['raw_message'] = service + " smoketest timed out."
        except subprocess.CalledProcessError:
            result['success'] = 0  # Failure
            result['raw_message'] = f"Error for service {service}: {e.stderr}"
         
        end_time = round(time.time())   
        result['duration'] = (end_time - start_time) * 1000
        
        if result['success'] == 1:
            result['raw_message'] = f"{service} smoketest is successful in {result['duration']} ms."
            
        with lock:
            raw_metrics[service] = result
        
        
            
        metric_service_success.labels(service=service).set(result['success'])
        metric_service_slowness.labels(service=service).set(result['slowness'])
        metric_service_duration.labels(service=service).set(result['duration'])
        # metric_service_raw_message.labels(service=service).set(result['raw_message'])
        
        write_log("INFO", result['raw_message'])
            
        time.sleep(running_interval)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str, help='Smoketest configuration.')
    parser.add_argument('-f', '--log-file', type=str, help='Log file output for script.')
    args = parser.parse_args()
    config_file_path = args.config

    log_file = args.log_file
    if not os.path.exists(log_file):
        open(log_file, 'a').close()
    
    try:
        handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=100000, backupCount=5)
        handler.terminator = ''  # Suppress newline
        global my_logger
        my_logger = logging.getLogger('MyLogger')
        my_logger.setLevel(logging.DEBUG)
        my_logger.addHandler(handler)
        console_handler = logging.StreamHandler()
        my_logger.addHandler(console_handler)
        print(f"Logging to file: {log_file}")
    except Exception as e:
        print(f"Error configuring logger: {e}")
        exit(1)

    # Load configuration
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
            print('INFO', 'Config file loaded successfully.')
    except IOError:
        print('ERROR', 'Config file doesn\'t exist.')
        write_log('ERROR', 'Config file doesn\'t exist.')
        exit(1)

    # Start Prometheus HTTP server to expose metrics
    start_http_server(9111)
    metric_smoketest_exporter_status.set(1)  # Set exporter status to running
    
    # Start smoketests in separate threads
    threads = []
    for service in config['services']:
        with lock:
            raw_metrics[service] = None
        print('INFO', f'running {service} smoketest')
        write_log('INFO', f'running {service} smoketest')
        thread = threading.Thread(target=smoketest, args=(config, service))
        thread.daemon = True
        threads.append(thread)
        thread.start()
        
    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    main()