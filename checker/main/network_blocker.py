import os
import platform



REDIRECT_IP = "127.0.0.1"

def get_hosts_file_path():
    system = platform.system().lower()
    if "windows" in system:
        return r"C:\Windows\System32\drivers\etc\hosts"
    elif "linux" in system or "darwin" in system:
        return "/etc/hosts"
    else:
        raise OSError("Invalid OS error")

def block_sites(BLOCKED_SITES):
    hosts_path = get_hosts_file_path()

    try:
        with open(hosts_path, "r+") as file:
            lines = file.readlines()
            file.seek(0, 0)

            for site_id, site_url in BLOCKED_SITES.items():
                entry = f"{REDIRECT_IP} {site_url}\n"
                if entry not in lines:
                    file.write(entry)
            file.writelines(lines)

        print("Сайты успешно заблокированы.")
    except PermissionError:
        print("Нет доступа! Запустите скрипт с правами администратора.")
    except Exception as e:
        print(f"Ошибка: {e}")

def unblock_sites(BLOCKED_SITES):
    hosts_path = get_hosts_file_path()

    try:
        with open(hosts_path, "r+") as file:
            lines = file.readlines()
            file.seek(0)

            for line in lines:
                if not any(site_url in line for site_url in BLOCKED_SITES.values()):
                    file.write(line)

            file.truncate()
        print("Сайты успешно разблокированы.")
    except PermissionError:
        print("Нет доступа! Запустите скрипт с правами администратора.")
    except Exception as e:
        print(f"Ошибка: {e}")

