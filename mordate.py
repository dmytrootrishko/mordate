import subprocess
import time
import os
import sys
import json
from pathlib import Path

def load_config(dir):
    config_path = os.path.join(dir, "mordate.json")

    default_config = {
        "pageant_path": "C:\\Program Files\\Five-BN\\putty\\PAGEANT.EXE",
        "pageant_params": [],
        "tortoise_path": "C:\\Program Files\\TortoiseSVN\\bin\\TortoiseProc.exe",
        "projects_filename": "projects.txt"
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка чтения конфига: {e}")
            return default_config
    else:
        print("Конфиг не найден.")
        return default_config

def is_process_running(process_name):
    try:
        output = subprocess.check_output('tasklist', shell=True).decode('cp866', errors='ignore')
        return process_name.lower() in output.lower()
    except Exception as e:
        print(f"Ошибка при проверке процессов: {e}")
        return False

def run_processes():
    if "-noclose" in sys.argv:
        is_noclose_arg = True
        sys.argv.remove("-noclose")
    else:
        is_noclose_arg = False

    if "-folder" in sys.argv:
        is_folder_arg = True
        sys.argv.remove("-folder")
    else:
        is_folder_arg = False

    if getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(sys.executable)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    config = load_config(script_dir)

    pageant_path = config["pageant_path"]
    pagent_exe_name = os.path.basename(pageant_path)
    pageant_params = config["pageant_params"]
    tortoise_path = config["tortoise_path"]
    projects_filename = config["projects_filename"]

    try:
        if not is_folder_arg:
            if len(sys.argv) > 1:
                projects_file = sys.argv[1]
                print(f"Используется пользовательский путь к файлу проектов: {projects_file}")
            else:
                projects_file = os.path.join(script_dir, projects_filename)
                print(f"Используется путь к файлу проектов по умолчанию: {projects_file}")
        else:
            if len(sys.argv) > 1:
                projects_folder_path = sys.argv[1]
                print(f"Используется поиск svn проектов по директории: {projects_folder_path}")
            else:
                print ("Вы не указали в какой папке искать проекты для SVN update.")
                return

        print("Очистка DNS...")
        subprocess.run("ipconfig /flushdns", shell=True, check=True)
        print("DNS успешно очищен.")

        if is_process_running(pagent_exe_name):
            print(f"{pagent_exe_name} уже запущен. Пропускаем запуск.")
        elif len(pageant_params) == 0:
            print(f"Не заданы ключи {pagent_exe_name}. Пропускаем запуск.")
        else:
            print(f"Запуск {pageant_path}...")
            putty_proc = subprocess.Popen([pageant_path] + pageant_params)
        
            time.sleep(2)

            if putty_proc.poll() is None:
                print(f"Процесс {pageant_path} успешно запущен (PID: {putty_proc.pid}).")
            else:
                print(f"Ошибка: {pageant_path} закрылся сразу после запуска с кодом {putty_proc.returncode}.")
                return

        if is_folder_arg or os.path.exists(projects_file):
            if not is_folder_arg:
                with open(projects_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if not content:
                    print(f"Файл {projects_file} пуст. SVN update пропущено.")
                    return
                
                formatted_paths = content.replace('\r\n', '*').replace('\n', '*')

            else:
                base_path = Path(projects_folder_path)
                svn_dirs = [str(d) for d in base_path.iterdir() if d.is_dir() and (d / ".svn").exists()]
                
                print("Найдены следущие проекты:")
                for svn_dir in svn_dirs:
                    print(svn_dir)

                formatted_paths = "*".join(svn_dirs)

            svn_args = [
                        tortoise_path,
                        "/command:update",
                        "/closeonend:2",
                        "/path",
                        formatted_paths
                    ]
                
            if is_noclose_arg:
                 svn_args.pop(2)

            print(f"Запуск SVN update...")
            subprocess.Popen(svn_args)
            print("Готово.")

        else:
            print(f"Файл {projects_file} не найден. SVN update пропущено.")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении системной команды: {e}")
    except FileNotFoundError as e:
        print(f"Ошибка: Файл не найден. Проверьте пути к exe файлам. {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    run_processes()