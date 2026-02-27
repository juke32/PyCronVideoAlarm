import sys
import logging
import argparse
import datetime


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Check if file logging should be enabled
    try:
        from core.config import get_config
        from core.logging_utils import setup_file_logging
        
        config = get_config()
        if config.get("logging", "file_logging_enabled"):
            setup_file_logging()
    except Exception as e:
        logging.error(f"Failed to setup file logging from config: {e}")

def main():
    if sys.platform == "win32":
        try:
            import ctypes
            # Tell Windows this is a distinct app, not just "python.exe" so the taskbar icon groups properly
            myappid = 'pycron.videoalarm.app.1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # macOS frozen app: set CWD to the folder containing the .app bundle.
    # Without this, macOS launches apps with CWD="/", so all relative paths
    # (video/, audio/, settings.json) resolve to root instead of the portable folder.
    if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
        import os as _os
        exe = _os.path.abspath(sys.executable)
        if '.app/Contents/MacOS' in exe:
            # exe = /path/to/App.app/Contents/MacOS/<binary>  →  dirname x4 = /path/to/
            portable_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(exe))))
            _os.chdir(portable_root)

    setup_logging()
    parser = argparse.ArgumentParser(description="Video Alarm Rebuilt")
    parser.add_argument("--test-alarm", action="store_true", help="Trigger alarm immediately for testing")
    parser.add_argument("--check", action="store_true", help="Check environment and exit")
    parser.add_argument("--execute-sequence", type=str, help="Execute a saved sequence by name")
    parser.add_argument("--delete-after", action="store_true", help="Delete the cron job after executing (for one-time alarms)")
    parser.add_argument('--job-id', help='Unique Cron Job ID for targeted deletion')
    parser.add_argument('--scheduled-time', help='Scheduled time (HH:MM) to verify deletion target')
    args = parser.parse_args()

    if args.check:
        logging.info("Checking environment...")
        try:
            from core.factory import get_platform_managers
            pm, dm = get_platform_managers()
            logging.info(f"Platform Managers Loaded: {pm.__class__.__name__}, {dm.__class__.__name__}")
            logging.info("Environment check passed.")
        except Exception as e:
            logging.error(f"Environment check failed: {e}")
            sys.exit(1)
        return
    
    # Execute sequence (called by cron/task scheduler)
    if args.execute_sequence:
        import os
        
        # Determine project root — different for frozen (PyInstaller) vs development
        if getattr(sys, 'frozen', False):
            # Frozen: executable lives in dist/ (Linux/Win) or App.app/Contents/MacOS/ (macOS)
            exe_path = os.path.abspath(sys.executable)
            if sys.platform == 'darwin' and '.app/Contents/MacOS' in exe_path:
                # sys.executable = /path/to/App.app/Contents/MacOS/PyCronVideoAlarm
                # dirname x4 reaches the folder containing the .app (where video/, audio/ live)
                project_root = os.path.dirname(           # /path/to/
                    os.path.dirname(                       # App.app
                        os.path.dirname(                   # Contents
                            os.path.dirname(exe_path))))   # MacOS
            else:
                project_root = os.path.dirname(exe_path)
        else:
            # Development: src/main.py → project root is one level up
            project_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
            
        from core.config import get_app_data_dir
        
        # We don't necessarily need to change directory to project root anymore for config/sequences, 
        # but it might be needed if they have local media in `video/`.
        os.chdir(project_root)
        
        # On Linux, setup environment for headless/cron execution
        if sys.platform.startswith('linux'):
            try:
                from platforms.linux.session import ensure_cron_environment
                ensure_cron_environment()
            except Exception as e:
                logging.warning(f"Session setup failed: {e}")
        
        logging.info(f"Executing sequence: {args.execute_sequence}")
        logging.info(f"  CWD: {os.getcwd()}")
        
        try:
            from logic.sequence import AlarmSequence
            from logic.actions import execute_action
            
            # Use AppData path for executing sequences instead of root project directory
            seq_dir = os.path.join(get_app_data_dir(), "sequences")
            
            # Handle testing temporary sequences which are pushed to temp/
            if args.execute_sequence.startswith("temp/") or args.execute_sequence.startswith("temp\\"):
                seq_file = os.path.join(seq_dir, f"{args.execute_sequence}.json")
            else:
                seq_file = os.path.join(seq_dir, f"{args.execute_sequence}.json")
            
            if not os.path.exists(seq_file):
                # Fallback to absolute if the passed sequence is already an absolute path
                if os.path.isabs(args.execute_sequence) and os.path.exists(args.execute_sequence):
                    seq_file = args.execute_sequence
                else:
                    logging.error(f"Sequence file not found: {seq_file}")
                    logging.error(f"  Available: {os.listdir(seq_dir) if os.path.exists(seq_dir) else 'dir not found'}")
                    sys.exit(1)
            
            sequence = AlarmSequence.load(seq_file)
            logging.info(f"Loaded sequence '{sequence.name}' with {len(sequence.actions)} actions")
            # Execute actions
            
            for i, action in enumerate(sequence.actions):
                logging.info(f"Executing action {i+1}/{len(sequence.actions)}: {action.action_type}")
                execute_action(action.action_type, action.config)
            
            logging.info("Sequence execution completed")
            
            # Delete if requested
            if args.delete_after:
                logging.info(f"Attempting to delete one-time job for '{args.execute_sequence}'...")
                try:
                    import os
                    if sys.platform == 'darwin':
                        # macOS: remove the launchd plist identified by job-id
                        try:
                            import glob
                            import plistlib
                            import subprocess as _sp
                            plist_dir = os.path.expanduser("~/Library/LaunchAgents")
                            label_prefix = "com.juke32.pycronvideoalarm"
                            deleted = False

                            if args.job_id:
                                plist_file = os.path.join(plist_dir, f"{label_prefix}.{args.job_id}.plist")
                                if os.path.exists(plist_file):
                                    _sp.run(["launchctl", "unload", plist_file],
                                            capture_output=True)
                                    os.remove(plist_file)
                                    logging.info(f"Deleted launchd plist by job-id: {args.job_id}")
                                    deleted = True

                            if not deleted:
                                # Fallback: match by sequence name in plist EnvironmentVariables
                                for plist_file in glob.glob(
                                        os.path.join(plist_dir, f"{label_prefix}.*.plist")):
                                    try:
                                        with open(plist_file, "rb") as f:
                                            plist = plistlib.load(f)
                                        env = plist.get("EnvironmentVariables", {})
                                        if (env.get("PCVA_SEQUENCE") == args.execute_sequence
                                                and env.get("PCVA_ONE_TIME") == "1"):
                                            _sp.run(["launchctl", "unload", plist_file],
                                                    capture_output=True)
                                            os.remove(plist_file)
                                            logging.info(f"Deleted launchd plist by sequence name: {plist_file}")
                                            deleted = True
                                            break
                                    except Exception:
                                        continue

                            if not deleted:
                                logging.warning("Could not find launchd plist to delete.")
                        except Exception as e:
                            logging.error(f"Failed to delete launchd plist: {e}")

                    elif sys.platform.startswith('linux'):
                        # Linux: remove cron job by matching our unique ID + marker
                        try:
                            from crontab import CronTab
                            cron = CronTab(user=True)
                            job_deleted = False

                            # Strategy 1: Unique Job ID (Best)
                            if args.job_id:
                                target_comment = f"#PyCronVideoAlarm:{args.job_id}"
                                for job in cron:
                                    if job.comment == target_comment:
                                        base_cmd = f'--execute-sequence "{args.execute_sequence}"'
                                        if base_cmd in str(job.command):
                                            cron.remove(job)
                                            job_deleted = True
                                            logging.info(f"Deleted cron job by ID {args.job_id}")
                                            break

                            # Strategy 2: Time-based Match
                            if not job_deleted and args.scheduled_time:
                                try:
                                    target_h, target_m = map(int, args.scheduled_time.split(':'))
                                    for job in cron:
                                        is_our_job = job.comment and (
                                            job.comment == "#PyCronVideoAlarm"
                                            or job.comment.startswith("#PyCronVideoAlarm:"))
                                        if (is_our_job
                                                and args.execute_sequence in str(job.command)
                                                and "--delete-after" in str(job.command)
                                                and job.hour == target_h
                                                and job.minute == target_m):
                                            cron.remove(job)
                                            job_deleted = True
                                            logging.info(f"Deleted cron job by time match")
                                            break
                                except Exception as e:
                                    logging.warning(f"Time match logic error: {e}")

                            if job_deleted:
                                cron.write()
                            else:
                                logging.warning("Could not find matching cron job to delete.")
                        except Exception as e:
                            logging.error(f"Failed to delete cron job: {e}")
                    else:
                        # Windows: use scheduler wrapper
                        from logic.scheduler import AlarmScheduler
                        scheduler = AlarmScheduler()
                        now = datetime.datetime.now()
                        time_str = f"{now.hour}:{now.minute:02d}"
                        scheduler.remove_alarm(args.execute_sequence, time_str)
                except Exception as e:
                    logging.error(f"Error deleting alarm: {e}")
            
        except Exception as e:
            logging.exception(f"Failed to execute sequence: {e}")
            sys.exit(1)
        return

    logging.info("Starting Video Alarm Dashboard...")
    from ui.main_window import VideoAlarmMainWindow
    app = VideoAlarmMainWindow()
    
    if args.test_alarm:
        app.after(1000, app.test_alarm)
        
    app.mainloop()

if __name__ == "__main__":
    main()
