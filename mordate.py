import subprocess
import time
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Any
from colorama import Fore

def load_config(dir) -> dict[str, Any]:
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
            print(f"{Fore.RED}Ошибка чтения конфига:{Fore.RESET} {e}")
            return default_config
    else:
        print(f"{Fore.RED}Конфиг не найден!{Fore.RESET}")
        return default_config

def get_script_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))
    
def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Автоматическое обновление проектов.")
    parser.add_argument("-d", "--scan-directory", action='append', default=[],
                        help="Путь к директории для поиска проектов SVN. Можно указать несколько раз.")
    parser.add_argument("-f", "--projects-file", action='append', default=[],
                        help="Путь к файлу со списком проектов. Можно указать несколько раз.")
    parser.add_argument("-n", "--no-close", action="store_true",
                        help="Если флаг установлен, то окно SVN не будет автоматически закрываться после завершения update.")
    return parser

def run_processes():
    script_dir = get_script_dir()
    config = load_config(script_dir)
    args = get_arg_parser().parse_args()
    
    try:
        if not run_peagent_process(config):
            return
        
        clean_dns_cache()

        svn_update_projects(config, args.no_close, args.scan_directory, args.projects_file, script_dir)

    except subprocess.CalledProcessError as e:
        print(f"{Fore.RED}Ошибка при выполнении системной команды:{Fore.RESET} {e}")
    except FileNotFoundError as e:
        print(f"{Fore.RED}Ошибка: Файл не найден. Проверьте пути к exe файлам.{Fore.RESET} {e}")
    except Exception as e:
        print(f"{Fore.RED}Произошла ошибка:{Fore.RESET} {e}")

def is_process_running(process_name: str) -> bool:
    try:
        output = subprocess.check_output('tasklist', shell=True).decode('cp866', errors='ignore')
        return process_name.lower() in output.lower()
    except Exception as e:
        print(f"{Fore.RED}Ошибка при проверке процессов:{Fore.RESET} {e}")
        return False

def run_peagent_process(config: dict[str, Any]) -> bool:
    pageant_path = config["pageant_path"]
    pagent_exe_name = os.path.basename(pageant_path)
    pageant_params = config["pageant_params"]

    if is_process_running(pagent_exe_name):
        print(f"{Fore.YELLOW}{pagent_exe_name} уже запущен. Пропускаем запуск.{Fore.RESET}")
    elif len(pageant_params) == 0:
        print(f"{Fore.YELLOW}Не заданы ключи {pagent_exe_name}. Пропускаем запуск.{Fore.RESET}")
    else:
        print(f"Запуск {pageant_path}...")
        putty_proc = subprocess.Popen([pageant_path] + pageant_params)
        
        time.sleep(2)

        if putty_proc.poll() is None:
            print(f"{Fore.GREEN}Процесс {pageant_path} успешно запущен (PID: {putty_proc.pid}).{Fore.RESET}")
        else:
            print(f"{Fore.RED}Ошибка: {pageant_path} закрылся сразу после запуска с кодом {putty_proc.returncode}.{Fore.RESET}")
            return False
    return True

def clean_dns_cache():
    print("Очистка DNS...")
    subprocess.run("ipconfig /flushdns", shell=True, check=True)
    print(f"{Fore.GREEN}DNS успешно очищен.{Fore.RESET}")

def svn_scan_directory(dirs: list[str]) -> list[str]:
    path_projects = []
    for dir in dirs:
        base_path = Path(dir)
        svn_dirs = [str(d) for d in base_path.iterdir() if d.is_dir() and (d / ".svn").exists()]
        path_projects.extend(svn_dirs)
    return path_projects

def svn_load_file_projects(files: list[str]) -> list[str]:
    path_projects = []
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"{Fore.YELLOW}Предупреждение: Файл '{file_path}' не найден. Пропускаю...{Fore.RESET}")
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                project_path = line.strip()
                
                if not project_path:
                    continue
                
                if os.path.exists(project_path):
                    path_projects.append(project_path)
                else:
                    print(f"{Fore.YELLOW}Предупреждение: Путь проекта '{project_path}' не существует. Пропускаю...{Fore.RESET}")
                    
    return path_projects

def svn_update_projects(config: dict[str, Any], no_close: bool, dirs: list[str], files: list[str], script_dir: str):
    path_projects = []
    path_projects.extend(svn_scan_directory(dirs))
    path_projects.extend(svn_load_file_projects(files))

    if not dirs and not files:
        files = [os.path.join(script_dir, config["projects_filename"])]
        path_projects.extend(svn_load_file_projects(files))

    if not path_projects:
        print(f"{Fore.YELLOW}Предупреждение: Не заданы проекты. SVN update пропущено.{Fore.RESET}")
        return

    print("Найдены следущие проекты:")
    for dir in path_projects:
        print(dir)

    formatted_paths = '*'.join(path_projects)

    svn_args = [
        config["tortoise_path"],
        "/command:update",
        "/path",
        formatted_paths
    ]
                
    if not no_close:
        svn_args.insert(2, "/closeonend:2")

    print("Запуск SVN update...")
    subprocess.Popen(svn_args)
    print(f"{Fore.GREEN}Готово.{Fore.RESET}")

if __name__ == "__main__":
    run_processes()