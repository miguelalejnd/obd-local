import obd
import threading
import time
import os
import requests
from flask import Flask, Response
from elm import Elm


app = Flask(__name__)

interval = 5  # in seconds

directory = '/tmp/obd-app/'
file_name = '/tmp/obd-app/id'
auth_value = '-1'

if not os.path.exists(directory):
    os.makedirs(directory)

if os.path.exists(file_name):
    with open(file_name, 'r') as file:
    # Leer el contenido del archivo y guardarlo en la variable auth_value
        auth_value = file.read()
else:
    with open(file_name, 'w') as file:
    # Escribir -1, el contenido de la var auth_value.
        file.write(auth_value)

### Emulador ###

# instanciar y obtener puerto
emulator = Elm(batch_mode=True)
pty = emulator.get_pty()

# Función para ejecutarlo
def run_emulator():
    emulator.run()

# Crear y ejecutar el hilo
thread_emulator = threading.Thread(target=run_emulator)
thread_emulator.start()
print(f'Emulador ELM327 running on port {pty}')
print()

# Establcer la concexión de la biblioteca python-OBD con el emulador
connection = obd.OBD(pty)

### Envío ###

# Función para leer los datos del vehículo con python-OBD
def get_data():

    barometric_pressure = connection.query(obd.commands.BAROMETRIC_PRESSURE)
    
    throttle_position = connection.query(obd.commands.THROTTLE_POS)
    speed = connection.query(obd.commands.SPEED)
    engine_rpm = connection.query(obd.commands.RPM)
    
    engine_load = connection.query(obd.commands.ENGINE_LOAD)
    engine_runtime = connection.query(obd.commands.RUN_TIME)
    control_module_voltage = connection.query(obd.commands.CONTROL_MODULE_VOLTAGE)
    
    maf = connection.query(obd.commands.MAF)
    intake_temp = connection.query(obd.commands.INTAKE_TEMP)
    intake_pressure = connection.query(obd.commands.INTAKE_PRESSURE)
    
    data = {
		'barometric_pressure': [barometric_pressure.value.magnitude, str(barometric_pressure.value.units)],
		
		'throttle_position': [throttle_position.value.magnitude, str(throttle_position.value.units)],
		'vehicle_speed': [speed.value.magnitude, str(speed.value.units)],
		'engine_rpm': [engine_rpm.value.magnitude, str(engine_rpm.value.units)],
		
		'engine_load': [engine_load.value.magnitude, str(engine_load.value.units)],
		'engine_runtime': [engine_runtime.value.magnitude, str(engine_runtime.value.units)],
		'control_module_voltage': [control_module_voltage.value.magnitude, str(control_module_voltage.value.units)],
		
		'maf': [maf.value.magnitude, str(maf.value.units)],
		'intake_temperature': [intake_temp.value.magnitude, str(intake_temp.value.units)],
		'intake_pressure': [intake_pressure.value.magnitude, str(intake_pressure.value.units)]
    }

    return data

# Funcion para enviar los datos al servicio central
def send_data_periodically():
    global auth_value
    while True:
        data = get_data()
        
        try:
            requests.post(f'http://localhost:35000/data/{auth_value}/',
                          json=data,
                          headers={'Content-Type': 'application/json'},
                          verify=False
            )
            print(f'Sending data to http://localhost:35000/data/{auth_value}/')
        except Exception as e:
            print("Connection error, service not reachable")
            print(f'URL: http://localhost:35000/data/{auth_value}')
        
        time.sleep(interval)

# Crear y ejecutar el hilo para el servidor web y sus dos endpoints

### server ###
@app.route('/<vehicle_id>/')
def save_token(vehicle_id):
    with open(file_name, 'w') as file:
        file.truncate(0)
        file.write(str(vehicle_id))

    globals()["auth_value"] = vehicle_id
    print('Value for authentication received ' + globals()["auth_value"])
    
    return ('', 204)

@app.route('/')
def test():
    return ('', 200)

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5001)).start()

send_data_periodically()
