
import sys
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

# Windows specific
try:
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    # Fallback/Mock for Linux devs or fresh installs
    logging.warning("pywin32 not found. Windows scheduling will not work.")


# Windows Task Scheduler API via pywin32 - Make sure to use the right folder :0
class WindowsScheduler:
    """Windows-specific scheduler using Task Scheduler API via pywin32"""
    TASK_FOLDER_NAME = "\\PyCronVideoAlarm"

    def __init__(self):
        self.scheduler = None
        self.root_folder = None
        self.task_folder = None

        if HAS_WIN32 and sys.platform == "win32":
            try:
                self.scheduler = win32com.client.Dispatch('Schedule.Service')
                self.scheduler.Connect()
                self.root_folder = self.scheduler.GetFolder("\\")
                
                # Create/Get subfolder to keep things clean
                try:
                    self.task_folder = self.root_folder.GetFolder(self.TASK_FOLDER_NAME)
                except Exception:
                    self.task_folder = self.root_folder.CreateFolder(self.TASK_FOLDER_NAME)
                    
            except Exception as e:
                logging.error(f"Windows Scheduler init failed: {e}")

    def get_debug_info(self) -> str:
        """Return a string containing debug information about scheduled tasks."""
        if not self.root_folder: return "Windows Scheduler not initialized."
        
        info = ["=== Windows Scheduler Debug Info ==="]
        
        folders = []
        if self.task_folder: folders.append(self.task_folder)
        if self.root_folder: folders.append(self.root_folder)
        
        for folder in folders:
            is_root = (folder == self.root_folder)
            header = "ROOT COMMANDS" if is_root else "PYCRON FOLDER"
            info.append(f"\n[{header}]")
            
            try:
                tasks = folder.GetTasks(0)
                for i in range(1, tasks.Count + 1):
                    t = tasks.Item(i)
                    
                    if is_root:
                         try:
                             if t.Definition.RegistrationInfo.Author != "PyCronVideoAlarm": continue
                         except: continue
                    
                    info.append(f"  - Name: {t.Name}")
                    info.append(f"    State: {t.State} (Enabled: {t.Enabled})")
                    try:
                        info.append(f"    Author: {t.Definition.RegistrationInfo.Author}")
                        info.append(f"    Desc: {t.Definition.RegistrationInfo.Description}")
                        info.append(f"    Next Run: {t.NextRunTime}")
                    except: pass
            except Exception as e:
                info.append(f"  Error listing folder: {e}")
                
        return "\n".join(info)

    def add_alarm(self, alarm_time: datetime, sequence_name: str, days: List[str], one_time: bool = True) -> (bool, str):
        """Add a new alarm task. Returns (Success, Message)."""
        if not self.scheduler or not self.task_folder: 
             return False, "Scheduler not initialized"
            
        try:
            task_def = self.scheduler.NewTask(0)
            
            # Registration Info
            reg_info = task_def.RegistrationInfo
            # STORE METADATA: PyCron|{sequence_name}|{time_str}
            time_str_meta = alarm_time.strftime('%H:%M')
            reg_info.Description = f"PyCron|{sequence_name}|{time_str_meta}"
            reg_info.Author = "PyCronVideoAlarm"
            
            # Settings
            settings = task_def.Settings
            settings.Enabled = True
            settings.StartWhenAvailable = True
            settings.WakeToRun = True
            settings.DisallowStartIfOnBatteries = False
            settings.StopIfGoingOnBatteries = False
            settings.Hidden = False
            
            # Triggers
            triggers = task_def.Triggers
            if one_time:
                trigger = triggers.Create(1) # 1 = TimeTrigger
                trigger.StartBoundary = alarm_time.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                trigger = triggers.Create(3) # 3 = WeeklyTrigger
                trigger.StartBoundary = alarm_time.strftime("%Y-%m-%dT%H:%M:%S")
                
                day_map = { "SUN": 1, "MON": 2, "TUE": 4, "WED": 8, "THU": 16, "FRI": 32, "SAT": 64 }
                mask = 0
                if not days: mask = 127 
                else:
                    for d in days: mask |= day_map.get(d.upper(), 0)
                trigger.DaysOfWeek = mask
                trigger.WeeksInterval = 1
            
            # Actions
            actions = task_def.Actions
            action = actions.Create(0) # 0 = Execute
            
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                action.Path = exe_path
                args = f'--execute-sequence "{sequence_name}"'
                if one_time: args += " --delete-after"
                action.Arguments = args
                action.WorkingDirectory = os.path.dirname(exe_path)
            else:
                action.Path = sys.executable
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                script_path = os.path.join(base_dir, "main.py")
                args = f'"{script_path}" --execute-sequence "{sequence_name}"'
                if one_time: args += " --delete-after"
                action.Arguments = args
                action.WorkingDirectory = base_dir
            
            # Save Task
            safe_seq_name = sequence_name.replace(" ", "_")
            task_name = f"{safe_seq_name}_{alarm_time.strftime('%H_%M')}"
            
            self.task_folder.RegisterTaskDefinition(
                task_name, task_def, 6, None, None, 3, None
            )
            logging.info(f"Task {task_name} created successfully")
            return True, f"Alarm set for {time_str_meta}"
            
        except Exception as e:
            logging.exception(f"Win Add Alarm failed: {e}") # Log full traceback
            return False, f"Failed to create task: {str(e)}"

    def _parse_task(self, task):
        # ... (Existing _parse_task implementation - unchanged)
        """Helper to parse a task object into an alarm dict. Returns None if invalid."""
        try:
            # STRATEGY 1: Metadata in Description (PyCron|Seq|Time)
            try:
                desc = task.Definition.RegistrationInfo.Description
                if desc and desc.startswith("PyCron|"):
                    parts = desc.split('|')
                    if len(parts) >= 3:
                        seq_name = parts[1]
                        time_str = parts[2]
                        # Get days logic (reuse existing)
                        days_display = "?"
                        try:
                            trig = task.Definition.Triggers.Item(1)
                            if trig.Type == 1: days_display = "Once"
                            elif trig.Type == 3: # Weekly
                                mask = trig.DaysOfWeek
                                d_list = []
                                if mask & 1: d_list.append("SUN")
                                if mask & 2: d_list.append("MON")
                                if mask & 4: d_list.append("TUE")
                                if mask & 8: d_list.append("WED")
                                if mask & 16: d_list.append("THU")
                                if mask & 32: d_list.append("FRI")
                                if mask & 64: d_list.append("SAT")
                                days_display = ",".join(d_list) if len(d_list) < 7 else "Daily"
                        except: pass
                        return {'time': time_str, 'sequence': seq_name, 'days': days_display, 'enabled': task.Enabled}
            except Exception: pass

            # STRATEGY 2: Legacy Filename Parsing
            if '_' in task.Name:
                parts = task.Name.rsplit('_', 2)
                if len(parts) == 3:
                     seq_name, hh, mm = parts
                     int(hh); int(mm)
                     days_display = "?"
                     try:
                         trig = task.Definition.Triggers.Item(1)
                         if trig.Type == 1: days_display = "Once"
                     except: pass
                     return {'time': f"{hh}:{mm}", 'sequence': seq_name, 'days': days_display, 'enabled': task.Enabled}
        except Exception: pass
        return None

    def list_alarms(self) -> List[Dict[str, Any]]:
        # ... (Existing list_alarms implementation)
        alarms = []
        folders = []
        if self.task_folder: folders.append(self.task_folder)
        if self.root_folder: folders.append(self.root_folder)
        for folder in folders:
            is_root = (folder == self.root_folder)
            try:
                tasks = folder.GetTasks(0)
                for i in range(1, tasks.Count + 1):
                    t = tasks.Item(i)
                    if is_root:
                        try:
                            if t.Definition.RegistrationInfo.Author != "PyCronVideoAlarm": continue
                        except: continue
                    alarm = self._parse_task(t)
                    if alarm: alarms.append(alarm)
            except Exception as e:
                logging.error(f"Failed to list alarms from {folder}: {e}")
        return alarms

    def remove_alarm(self, sequence_name, time_str, days_str="") -> (bool, str):
        """Remove alarm from Folder OR Root. Returns (Success, Message)."""
        if not self.root_folder: return False, "Scheduler not initialized"
        
        try:
            target_hh, target_mm = map(int, time_str.split(':'))
            
            folders_to_check = []
            if self.task_folder: folders_to_check.append(self.task_folder)
            folders_to_check.append(self.root_folder)
            
            logging.info(f"Removing alarm {sequence_name} at {time_str}...")
            
            for folder in folders_to_check:
                is_root = (folder == self.root_folder)
                try:
                    tasks = folder.GetTasks(0)
                    for i in range(1, tasks.Count + 1):
                        t = tasks.Item(i)
                        
                        # Root safety
                        if is_root:
                            try:
                                if t.Definition.RegistrationInfo.Author != "PyCronVideoAlarm": continue
                            except: continue

                        # A. METADATA MATCH
                        try:
                            desc = t.Definition.RegistrationInfo.Description
                            if desc and desc.startswith(f"PyCron|{sequence_name}|{time_str}"):
                                 folder.DeleteTask(t.Name, 0)
                                 msg = f"Deleted {t.Name} (Metadata Match)"
                                 logging.info(msg)
                                 return True, msg
                        except: pass
                        
                        # B. FILENAME MATCH
                        if '_' in t.Name:
                            try:
                                parts = t.Name.rsplit('_', 2)
                                if len(parts) == 3:
                                    s_name_file, h_str, m_str = parts
                                    if int(h_str) == target_hh and int(m_str) == target_mm:
                                        if s_name_file == sequence_name or s_name_file == sequence_name.replace(" ", "_"):
                                            folder.DeleteTask(t.Name, 0)
                                            msg = f"Deleted {t.Name} (Filename Match)"
                                            logging.info(msg)
                                            return True, msg
                            except ValueError: continue
                except Exception as e:
                    logging.warning(f"Error scanning folder: {e}")

            return False, f"Alarm '{sequence_name}' at {time_str} not found."
            
        except Exception as e:
            logging.exception(f"Remove alarm failed: {e}")
            return False, f"Error removing alarm: {str(e)}"
