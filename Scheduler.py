import subprocess
import time
from datetime import datetime
import signal
import os
import psutil
import threading
import queue

# ================================
# CENTRALIZED CONFIGURATION
# ================================
USERNAME = "thaniyanki"  # Change ONLY this line for different users
BASE_PATH = f"/home/{USERNAME}/Bots"

# Bot ON/OFF switches (True = ON, False = OFF)
WHATSAPP_BIRTHDAY_SWITCH = True # Set to False to disable WhatsApp bot
FACEBOOK_BIRTHDAY_SWITCH = True # Set to False to disable Facebook bot

# Define schedules (24-hour format) with start and stop times
WHATSAPP_BIRTHDAY_WISHER_SCHEDULE = {
    "monday":    {"start": "17:00:00", "stop": "18:00:00"},
    "tuesday":   {"start": "18:18:00", "stop": "20:00:00"},
    "wednesday": {"start": "15:45:00", "stop": "08:00:00"},
    "thursday":  {"start": "07:00:00", "stop": "08:00:00"},
    "friday":    {"start": "07:00:00", "stop": "08:00:00"},
    "saturday":  {"start": "07:00:00", "stop": "08:00:00"},
    "sunday":    {"start": "07:00:00", "stop": "08:00:00"},
}

FACEBOOK_BIRTHDAY_WISHER_SCHEDULE = {
    "monday":    {"start": "09:00:00", "stop": "10:00:00"},
    "tuesday":   {"start": "09:00:00", "stop": "10:00:00"},
    "wednesday": {"start": "09:00:00", "stop": "10:00:00"},
    "thursday":  {"start": "09:00:00", "stop": "10:00:00"},
    "friday":    {"start": "09:00:00", "stop": "10:00:00"},
    "saturday":  {"start": "09:00:00", "stop": "10:00:00"},
    "sunday":    {"start": "09:00:00", "stop": "10:00:00"},
}

# Bot paths and configurations (AUTOMATICALLY GENERATED)
BOT_CONFIGS = {
    "whatsapp birthday wisher": {
        "directory": f"{BASE_PATH}/WhatsApp birthday wisher",
        "script": "WhatsApp birthday wisher.py",
        "venv_path": f"{BASE_PATH}/WhatsApp birthday wisher/venv/bin/activate"
    },
    "facebook birthday wisher": {
        "directory": f"{BASE_PATH}/Facebook birthday wisher",
        "script": "Facebook birthday wisher.py",
        "venv_path": f"{BASE_PATH}/Facebook birthday wisher/venv/bin/activate"
    }
}

# ================================
# SCHEDULER CODE (NO CHANGES NEEDED BELOW)
# ================================

# Track running processes
running_processes = {}
output_queues = {}

def is_bot_running(process_name):
    """Check if the bot process is running using psutil"""
    bot_config = BOT_CONFIGS[process_name]
    script_name = bot_config["script"]
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'python' in cmdline and script_name in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except Exception:
        return False

def should_start_now(schedule):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    day_of_week = now.strftime("%A").lower()
    return current_time == schedule.get(day_of_week, {}).get("start", "")

def should_stop_now(schedule):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    day_of_week = now.strftime("%A").lower()
    return current_time == schedule.get(day_of_week, {}).get("stop", "")

def read_output(process_name, proc, output_queue):
    """Read output from process and put it in queue"""
    try:
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            output_queue.put((process_name, line))
    except:
        pass

def run_script(process_name):
    try:
        # Check if bot is already running
        if is_bot_running(process_name):
            print(f"[{datetime.now()}] {process_name} is already running. Skipping...")
            return
        
        # Get bot configuration
        bot_config = BOT_CONFIGS[process_name]
        script_path = os.path.join(bot_config["directory"], bot_config["script"])
        
        print(f"\n[{datetime.now()}] Starting {process_name}...")
        print("=" * 60)
        
        # Create the command to run
        command = (
            f"cd '{bot_config['directory']}' && "
            f"source '{bot_config['venv_path']}' && "
            f"exec python -u '{script_path}'"
        )
        
        # Run the process with real-time output capture
        proc = subprocess.Popen(
            command,
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            preexec_fn=os.setsid
        )
        
        # Create output queue and start reader thread
        output_queue = queue.Queue()
        output_queues[process_name] = output_queue
        reader_thread = threading.Thread(
            target=read_output,
            args=(process_name, proc, output_queue),
            daemon=True
        )
        reader_thread.start()
        
        running_processes[process_name] = {
            'process': proc,
            'thread': reader_thread,
            'start_time': datetime.now()
        }
        
        print(f"[{datetime.now()}] {process_name} started (PID: {proc.pid})")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error starting {process_name}: {e}")

def stop_script(process_name):
    try:
        if process_name not in running_processes and not is_bot_running(process_name):
            print(f"[{datetime.now()}] {process_name} was not running")
            return
        
        # Stop the process if we started it
        if process_name in running_processes:
            proc = running_processes[process_name]['process']
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=5)
                print(f"[{datetime.now()}] Stopped {process_name} (PID: {proc.pid})")
            except:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    print(f"[{datetime.now()}] Force stopped {process_name} (PID: {proc.pid})")
                except:
                    pass
            finally:
                if process_name in running_processes:
                    del running_processes[process_name]
                if process_name in output_queues:
                    del output_queues[process_name]
        
        # Also stop any other running instances
        bot_config = BOT_CONFIGS[process_name]
        script_name = bot_config["script"]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'python' in cmdline and script_name in cmdline:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except:
                        proc.kill()
                    print(f"[{datetime.now()}] Stopped stray {process_name} (PID: {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
    except Exception as e:
        print(f"[{datetime.now()}] Error stopping {process_name}: {e}")

def check_and_stop_bots():
    """Check if any bots need to be stopped based on schedule"""
    # Check WhatsApp Birthday Wisher
    if should_stop_now(WHATSAPP_BIRTHDAY_WISHER_SCHEDULE):
        if is_bot_running("whatsapp birthday wisher") or "whatsapp birthday wisher" in running_processes:
            print(f"[{datetime.now()}] Scheduled stop time reached for WhatsApp Birthday Wisher")
            stop_script("whatsapp birthday wisher")
    
    # Check Facebook Birthday Wisher
    if should_stop_now(FACEBOOK_BIRTHDAY_WISHER_SCHEDULE):
        if is_bot_running("facebook birthday wisher") or "facebook birthday wisher" in running_processes:
            print(f"[{datetime.now()}] Scheduled stop time reached for Facebook Birthday Wisher")
            stop_script("facebook birthday wisher")

def process_output():
    """Process and print output from running bots"""
    for process_name in list(output_queues.keys()):
        try:
            while True:
                try:
                    source, line = output_queues[process_name].get_nowait()
                    print(line, end='', flush=True)
                except queue.Empty:
                    break
        except:
            pass

if __name__ == "__main__":
    print("Scheduler bot started. Waiting for scheduled times...")
    print("Monitoring the following bots:")
    print("- WhatsApp Birthday Wisher")
    print("- Facebook Birthday Wisher")
    print(f"WhatsApp Birthday Switch: {'ON' if WHATSAPP_BIRTHDAY_SWITCH else 'OFF'}")
    print(f"Facebook Birthday Switch: {'ON' if FACEBOOK_BIRTHDAY_SWITCH else 'OFF'}")
    print(f"Username: {USERNAME}")
    print(f"Base Path: {BASE_PATH}")
    print("Press Ctrl+C to stop the scheduler")
    
    try:
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            
            # Process any available output from running bots
            process_output()
            
            # Check for bots that need to be stopped
            check_and_stop_bots()
            
            # Check WhatsApp Birthday Wisher (only if switch is ON)
            if WHATSAPP_BIRTHDAY_SWITCH and should_start_now(WHATSAPP_BIRTHDAY_WISHER_SCHEDULE):
                run_script("whatsapp birthday wisher")
                time.sleep(2)
            
            # Check Facebook Birthday Wisher (only if switch is ON)
            if FACEBOOK_BIRTHDAY_SWITCH and should_start_now(FACEBOOK_BIRTHDAY_WISHER_SCHEDULE):
                run_script("facebook birthday wisher")
                time.sleep(2)
            
            # Clean up completed processes
            for process_name in list(running_processes.keys()):
                proc = running_processes[process_name]['process']
                if proc.poll() is not None:  # Process has finished
                    # Print any remaining output
                    process_output()
                    if process_name in running_processes:
                        del running_processes[process_name]
                    if process_name in output_queues:
                        del output_queues[process_name]
                    print(f"[{datetime.now()}] {process_name} completed")
                    print("=" * 60)
            
            time.sleep(0.1)  # Check very frequently for output
            
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        # Stop all running bots before exiting
        for process_name in list(running_processes.keys()):
            stop_script(process_name)
        print("Scheduler stopped.")
