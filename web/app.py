import flask
import traceback
import sys
import os
import time
import io
import zipfile
import hashlib
sys.path.append('..')
from patcher import FirmwarePatcher

app = flask.Flask(__name__)


@app.errorhandler(Exception)
def handle_bad_request(e):
    return 'Exception occured:\n{}'.format(traceback.format_exc()), \
            400, {'Content-Type': 'text/plain'}

# http://flask.pocoo.org/snippets/40/
@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return flask.url_for(endpoint, **values)

@app.route('/cfw')
def patch_firmware():
    version = flask.request.args.get('version', None)
    if version not in ['DRV152', 'DRV155', 'DRV160']:
        return 'Invalid firmware version.', 400

    with open('bins/{}.bin'.format(version), 'rb') as fp:
        patcher = FirmwarePatcher(fp.read())

    kers_min_speed = flask.request.args.get('kers_min_speed', None)
    if kers_min_speed is not None:
        kers_min_speed = float(kers_min_speed)
        assert kers_min_speed >= 0 and kers_min_speed <= 65
        patcher.kers_min_speed(kers_min_speed)

    speed_params = flask.request.args.get('speed_params', None)
    if speed_params:
        speed_normal_kmh = int(flask.request.args.get('speed_sport_kmh', None))
        assert speed_normal_kmh >= 0 and speed_normal_kmh <= 65
        speed_normal_phase = int(flask.request.args.get('speed_sport_phase', None))
        assert speed_normal_phase >= 0 and speed_normal_phase <= 65535
        speed_normal_battery = int(flask.request.args.get('speed_sport_battery', None))
        assert speed_normal_battery >= 0 and speed_normal_battery <= 65535
        speed_eco_kmh = int(flask.request.args.get('speed_eco_kmh', None))
        assert speed_eco_kmh >= 0 and speed_eco_kmh <= 65
        speed_normal_kmh = int(flask.request.args.get('speed_normal_kmh', None))
        assert speed_normal_kmh >= 0 and speed_normal_kmh <= 65
        patcher.speed_params(speed_sport_kmh, speed_sport_phase, speed_sport_battery, speed_normal_kmh, speed_eco_kmh)

    brake_params = flask.request.args.get('brake_params', None)
    if brake_params:
        brake_limit = int(flask.request.args.get('brake_limit', None))
        assert brake_limit >= 1 and brake_limit <= 130
        brake_i_min = int(flask.request.args.get('brake_i_min', None))
        assert brake_i_min >= 0 and brake_i_min <= 65535
        brake_i_max = int(flask.request.args.get('brake_i_max', None))
        assert brake_i_max >= brake_i_min and brake_i_max <= 65535
        patcher.brake_params(brake_limit, brake_i_min, brake_i_max)

    motor_start_speed = flask.request.args.get('motor_start_speed', None)
    if motor_start_speed is not None:
        motor_start_speed = float(motor_start_speed)
        assert motor_start_speed >= 0 and motor_start_speed <= 100
        patcher.motor_start_speed(motor_start_speed)

    cruise_control_delay = flask.request.args.get('cruise_control_delay', None)
    if cruise_control_delay is not None:
        cruise_control_delay = float(cruise_control_delay)
        assert cruise_control_delay >= 0.1 and cruise_control_delay <= 20.0
        patcher.cruise_control_delay(cruise_control_delay)

    cruise_control_nobeep = flask.request.args.get('cruise_control_nobeep', None)
    if cruise_control_nobeep:
        patcher.cruise_control_nobeep()

    instant_eco_switch = flask.request.args.get('instant_eco_switch', None)
    if instant_eco_switch:
        patcher.instant_eco_switch()

    boot_with_eco = flask.request.args.get('boot_with_eco', None)
    if boot_with_eco:
        patcher.boot_with_eco()

    voltage_limit = flask.request.args.get('voltage_limit', None)
    if voltage_limit is not None:
        voltage_limit = float(voltage_limit)
        assert voltage_limit >= 43.01 and voltage_limit <= 100.00
        patcher.voltage_limit(voltage_limit)

    batt_saving_voltage_threshold = flask.request.args.get('batt_saving_voltage_threshold', None)
    if batt_saving_voltage_threshold is not None:
        batt_saving_voltage_threshold = int(batt_saving_voltage_threshold)
        assert batt_saving_voltage_threshold >= 30 and batt_saving_voltage_threshold <= 38
        patcher.batt_saving_voltage_threshold(batt_saving_voltage_threshold)

    russian_throttle = flask.request.args.get('russian_throttle', None)
    if russian_throttle:
        patcher.alt_throttle_alg()

    remove_hard_speed_limit = flask.request.args.get('remove_hard_speed_limit', None)
    if remove_hard_speed_limit:
        patcher.remove_hard_speed_limit()

    remove_charging_mode = flask.request.args.get('remove_charging_mode', None)
    if remove_charging_mode:
        patcher.remove_charging_mode()

    stay_on_locked = flask.request.args.get('stay_on_locked', None)
    if stay_on_locked:
        patcher.stay_on_locked()

    bms_uart_76800 = flask.request.args.get('bms_uart_76800', None)
    if bms_uart_76800:
        patcher.bms_uart_76800()

    wheel_speed_const = flask.request.args.get('wheel_speed_const', None)
    if wheel_speed_const:
        wheel_speed_const = int(wheel_speed_const)
        assert wheel_speed_const >= 200 and wheel_speed_const <= 500
        patcher.wheel_speed_const(wheel_speed_const)

    version_spoofing = flask.request.args.get('version_spoofing', None)
    if version_spoofing:

    # make zip file for firmware
    zip_buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False)

    zip_file.writestr('FIRM.bin', patcher.data)
    md5 = hashlib.md5()
    md5.update(patcher.data)

    patcher.encrypt()
    zip_file.writestr('FIRM.bin.enc', patcher.data)
    md5e = hashlib.md5()
    md5e.update(patcher.data)

    info_txt = 'dev: M365;\nnam: {};\nenc: B;\ntyp: DRV;\nmd5: {};\nmd5e: {};\n'.format(
        version, md5.hexdigest(), md5e.hexdigest())

    zip_file.writestr('info.txt', info_txt.encode())
    zip_file.comment = flask.request.url.encode()
    zip_file.close()
    zip_buffer.seek(0)
    content = zip_buffer.getvalue()
    zip_buffer.close()

    resp = flask.Response(content)
    filename = version + '-' + str(int(time.time())) + '.zip'
    resp.headers['Content-Type'] = 'application/zip'
    resp.headers['Content-Disposition'] = 'inline; filename="{0}"'.format(filename)
    resp.headers['Content-Length'] = len(content)

    return resp

if __name__ == '__main__':
    app.run('0.0.0.0')
