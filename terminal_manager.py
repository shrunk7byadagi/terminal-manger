#!/usr/bin/env python3
"""
Terminal Manager - GUI Interface for Terminal Operations
A comprehensive desktop application for managing terminal tasks with a user-friendly interface
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import subprocess
import threading
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
import re
import sys

class TerminalManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Terminal Manager - GUI Interface")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Configuration file for storing settings
        self.config_file = Path.home() / '.terminal_manager_config.json'
        self.config = self.load_config()
        
        # Current processes
        self.processes = {}
        self.current_ssh_process = None
        
        self.create_gui()
        self.load_ssh_connections()
        
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {
            'ssh_connections': [],
            'recent_files': [],
            'cron_jobs': [],
            'preferred_editor': 'nano'
        }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {e}")
    
    def create_gui(self):
        """Create the main GUI interface"""
        # Create status bar first (before tabs that might use it)
        self.status_bar = tk.Label(self.root, text="Initializing Terminal Manager...", 
                                  bd=1, relief=tk.SUNKEN, anchor=tk.W,
                                  bg='#404040', fg='white')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_file_editor_tab()
        self.create_cron_manager_tab()
        self.create_ssh_manager_tab()
        self.create_terminal_tab()
        self.create_system_monitor_tab()
        
        # Update status bar
        self.status_bar.config(text="Ready")
    
    def create_file_editor_tab(self):
        """Create file editor tab"""
        editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(editor_frame, text="File Editor")
        
        # Toolbar
        toolbar = ttk.Frame(editor_frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="New File", command=self.new_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Open File", command=self.open_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save File", command=self.save_file).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save As", command=self.save_file_as).pack(side='left', padx=2)
        
        ttk.Separator(toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        # Editor selection
        ttk.Label(toolbar, text="Editor:").pack(side='left', padx=2)
        self.editor_var = tk.StringVar(value=self.config.get('preferred_editor', 'nano'))
        editor_combo = ttk.Combobox(toolbar, textvariable=self.editor_var, 
                                   values=['nano', 'vim', 'vi', 'gedit', 'code'], width=8)
        editor_combo.pack(side='left', padx=2)
        editor_combo.bind('<<ComboboxSelected>>', self.on_editor_changed)
        
        ttk.Button(toolbar, text="Open in Terminal Editor", 
                  command=self.open_in_terminal_editor).pack(side='left', padx=5)
        
        # File info
        info_frame = ttk.Frame(editor_frame)
        info_frame.pack(fill='x', padx=5)
        
        self.file_path_var = tk.StringVar(value="New File")
        ttk.Label(info_frame, text="File:").pack(side='left')
        ttk.Label(info_frame, textvariable=self.file_path_var, relief='sunken').pack(side='left', fill='x', expand=True, padx=5)
        
        # Text editor
        text_frame = ttk.Frame(editor_frame)
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.text_editor = scrolledtext.ScrolledText(text_frame, wrap=tk.NONE, 
                                                    font=('Consolas', 11),
                                                    bg='#1e1e1e', fg='#d4d4d4',
                                                    insertbackground='white',
                                                    selectbackground='#264f78')
        self.text_editor.pack(fill='both', expand=True)
        
        # Recent files
        recent_frame = ttk.LabelFrame(editor_frame, text="Recent Files")
        recent_frame.pack(fill='x', padx=5, pady=5)
        
        self.recent_listbox = tk.Listbox(recent_frame, height=3, 
                                        bg='#2b2b2b', fg='white',
                                        selectbackground='#404040')
        self.recent_listbox.pack(fill='x', padx=5, pady=5)
        self.recent_listbox.bind('<Double-1>', self.open_recent_file)
        
        self.current_file_path = None
        self.update_recent_files()
    
    def create_cron_manager_tab(self):
        """Create cron job manager tab"""
        cron_frame = ttk.Frame(self.notebook)
        self.notebook.add(cron_frame, text="Cron Manager")
        
        # Toolbar
        cron_toolbar = ttk.Frame(cron_frame)
        cron_toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(cron_toolbar, text="Refresh Jobs", command=self.refresh_cron_jobs).pack(side='left', padx=2)
        ttk.Button(cron_toolbar, text="Add Job", command=self.add_cron_job).pack(side='left', padx=2)
        ttk.Button(cron_toolbar, text="Edit Job", command=self.edit_cron_job).pack(side='left', padx=2)
        ttk.Button(cron_toolbar, text="Delete Job", command=self.delete_cron_job).pack(side='left', padx=2)
        ttk.Button(cron_toolbar, text="View Logs", command=self.view_cron_logs).pack(side='left', padx=2)
        
        # Cron jobs list
        cron_list_frame = ttk.Frame(cron_frame)
        cron_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Treeview for cron jobs
        columns = ('Schedule', 'Command', 'Description', 'Status')
        self.cron_tree = ttk.Treeview(cron_list_frame, columns=columns, show='tree headings', height=10)
        
        self.cron_tree.heading('#0', text='#')
        self.cron_tree.column('#0', width=50)
        
        for col in columns:
            self.cron_tree.heading(col, text=col)
            if col == 'Command':
                self.cron_tree.column(col, width=300)
            elif col == 'Description':
                self.cron_tree.column(col, width=200)
            else:
                self.cron_tree.column(col, width=150)
        
        # Scrollbar for treeview
        cron_scrollbar = ttk.Scrollbar(cron_list_frame, orient='vertical', command=self.cron_tree.yview)
        self.cron_tree.configure(yscrollcommand=cron_scrollbar.set)
        
        self.cron_tree.pack(side='left', fill='both', expand=True)
        cron_scrollbar.pack(side='right', fill='y')
        
        # Cron job details
        details_frame = ttk.LabelFrame(cron_frame, text="Job Details")
        details_frame.pack(fill='x', padx=5, pady=5)
        
        self.cron_details = scrolledtext.ScrolledText(details_frame, height=6,
                                                     bg='#1e1e1e', fg='#d4d4d4')
        self.cron_details.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.cron_tree.bind('<<TreeviewSelect>>', self.on_cron_select)
        
        # Store cron jobs for easy access
        self.cron_jobs_list = []
        
        # Load initial cron jobs (with safe status bar access)
        self.root.after(100, self.refresh_cron_jobs)  # Delay to ensure GUI is fully created
    
    def create_ssh_manager_tab(self):
        """Create SSH connection manager tab"""
        ssh_frame = ttk.Frame(self.notebook)
        self.notebook.add(ssh_frame, text="SSH Manager")
        
        # Left panel - connections
        left_panel = ttk.Frame(ssh_frame)
        left_panel.pack(side='left', fill='y', padx=5, pady=5)
        
        # SSH toolbar
        ssh_toolbar = ttk.Frame(left_panel)
        ssh_toolbar.pack(fill='x', pady=(0, 5))
        
        ttk.Button(ssh_toolbar, text="Add", command=self.add_ssh_connection).pack(side='left', padx=2)
        ttk.Button(ssh_toolbar, text="Edit", command=self.edit_ssh_connection).pack(side='left', padx=2)
        ttk.Button(ssh_toolbar, text="Delete", command=self.delete_ssh_connection).pack(side='left', padx=2)
        
        # SSH connections list
        ttk.Label(left_panel, text="Saved Connections:").pack(anchor='w')
        
        self.ssh_listbox = tk.Listbox(left_panel, width=30, height=15,
                                     bg='#2b2b2b', fg='white',
                                     selectbackground='#404040')
        self.ssh_listbox.pack(fill='both', expand=True, pady=5)
        self.ssh_listbox.bind('<Double-1>', self.connect_ssh)
        
        # Quick connect
        quick_frame = ttk.LabelFrame(left_panel, text="Quick Connect")
        quick_frame.pack(fill='x', pady=5)
        
        ttk.Label(quick_frame, text="Host:").pack(anchor='w')
        self.quick_host = ttk.Entry(quick_frame)
        self.quick_host.pack(fill='x', pady=2)
        
        ttk.Label(quick_frame, text="User:").pack(anchor='w')
        self.quick_user = ttk.Entry(quick_frame)
        self.quick_user.pack(fill='x', pady=2)
        
        ttk.Button(quick_frame, text="Connect", command=self.quick_ssh_connect).pack(pady=5)
        
        # Right panel - SSH session
        right_panel = ttk.Frame(ssh_frame)
        right_panel.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        
        # SSH session controls
        session_toolbar = ttk.Frame(right_panel)
        session_toolbar.pack(fill='x', pady=(0, 5))
        
        ttk.Button(session_toolbar, text="Connect Selected", command=self.connect_ssh).pack(side='left', padx=2)
        ttk.Button(session_toolbar, text="Disconnect", command=self.disconnect_ssh).pack(side='left', padx=2)
        ttk.Button(session_toolbar, text="Clear Output", command=self.clear_ssh_output).pack(side='left', padx=2)
        
        # SSH output
        self.ssh_output = scrolledtext.ScrolledText(right_panel, 
                                                   bg='#1e1e1e', fg='#00ff00',
                                                   font=('Consolas', 10))
        self.ssh_output.pack(fill='both', expand=True)
        
        # SSH input
        input_frame = ttk.Frame(right_panel)
        input_frame.pack(fill='x', pady=5)
        
        ttk.Label(input_frame, text="Command:").pack(side='left')
        self.ssh_input = ttk.Entry(input_frame)
        self.ssh_input.pack(side='left', fill='x', expand=True, padx=5)
        self.ssh_input.bind('<Return>', self.send_ssh_command)
        
        ttk.Button(input_frame, text="Send", command=self.send_ssh_command).pack(side='right')
        
        # SSH command history
        self.ssh_history = []
        self.ssh_history_index = -1
        self.ssh_input.bind('<Up>', self.ssh_history_up)
        self.ssh_input.bind('<Down>', self.ssh_history_down)
    
    def create_terminal_tab(self):
        """Create integrated terminal tab"""
        terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(terminal_frame, text="Terminal")
        
        # Terminal toolbar
        term_toolbar = ttk.Frame(terminal_frame)
        term_toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(term_toolbar, text="Clear", command=self.clear_terminal).pack(side='left', padx=2)
        ttk.Button(term_toolbar, text="Stop Process", command=self.stop_terminal_process).pack(side='left', padx=2)
        
        ttk.Separator(term_toolbar, orient='vertical').pack(side='left', padx=5, fill='y')
        
        ttk.Label(term_toolbar, text="Working Dir:").pack(side='left', padx=2)
        self.working_dir = ttk.Entry(term_toolbar, width=50)
        self.working_dir.insert(0, os.getcwd())
        self.working_dir.pack(side='left', padx=2)
        
        ttk.Button(term_toolbar, text="Browse", command=self.browse_working_dir).pack(side='left', padx=2)
        ttk.Button(term_toolbar, text="Set Dir", command=self.set_working_dir).pack(side='left', padx=2)
        
        # Terminal output
        self.terminal_output = scrolledtext.ScrolledText(terminal_frame,
                                                        bg='#000000', fg='#00ff00',
                                                        font=('Consolas', 10),
                                                        wrap=tk.WORD)
        self.terminal_output.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Terminal input
        input_frame = ttk.Frame(terminal_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(input_frame, text="$").pack(side='left')
        self.terminal_input = ttk.Entry(input_frame, font=('Consolas', 10))
        self.terminal_input.pack(side='left', fill='x', expand=True, padx=5)
        self.terminal_input.bind('<Return>', self.execute_terminal_command)
        self.terminal_input.bind('<Up>', self.terminal_history_up)
        self.terminal_input.bind('<Down>', self.terminal_history_down)
        
        ttk.Button(input_frame, text="Execute", command=self.execute_terminal_command).pack(side='right')
        
        # Command history
        self.command_history = []
        self.history_index = -1
        
        # Welcome message
        self.terminal_output.insert(tk.END, "Terminal Manager - Integrated Terminal\n")
        self.terminal_output.insert(tk.END, f"Working directory: {os.getcwd()}\n")
        self.terminal_output.insert(tk.END, "Type commands below. Use 'help' for built-in help.\n\n")
    
    def create_system_monitor_tab(self):
        """Create system monitoring tab"""
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text="System Monitor")
        
        # Monitor toolbar
        monitor_toolbar = ttk.Frame(monitor_frame)
        monitor_toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(monitor_toolbar, text="Refresh", command=self.refresh_system_info).pack(side='left', padx=2)
        ttk.Button(monitor_toolbar, text="Kill Process", command=self.kill_process).pack(side='left', padx=2)
        ttk.Button(monitor_toolbar, text="System Logs", command=self.view_system_logs).pack(side='left', padx=2)
        
        # Auto refresh
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(monitor_toolbar, text="Auto Refresh (5s)", 
                       variable=self.auto_refresh_var,
                       command=self.toggle_auto_refresh).pack(side='left', padx=10)
        
        # System info notebook
        info_notebook = ttk.Notebook(monitor_frame)
        info_notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # System overview
        overview_frame = ttk.Frame(info_notebook)
        info_notebook.add(overview_frame, text="Overview")
        
        self.system_info = scrolledtext.ScrolledText(overview_frame, height=10,
                                                    bg='#1e1e1e', fg='#d4d4d4',
                                                    font=('Consolas', 10))
        self.system_info.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Process list
        process_frame = ttk.Frame(info_notebook)
        info_notebook.add(process_frame, text="Processes")
        
        # Process tree
        process_columns = ('PID', 'Name', 'CPU%', 'Memory', 'User')
        self.process_tree = ttk.Treeview(process_frame, columns=process_columns, show='headings', height=15)
        
        for col in process_columns:
            self.process_tree.heading(col, text=col)
            self.process_tree.column(col, width=100)
        
        process_scrollbar = ttk.Scrollbar(process_frame, orient='vertical', command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=process_scrollbar.set)
        
        self.process_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        process_scrollbar.pack(side='right', fill='y')
        
        # Auto refresh control
        self.auto_refresh_job = None
        
        # Start auto refresh (with safe status bar access)
        self.root.after(200, self.refresh_system_info)  # Delay to ensure GUI is ready
        self.root.after(300, self.schedule_auto_refresh)  # Delay to start auto-refresh
    
    # File Editor Methods
    def new_file(self):
        """Create a new file"""
        self.text_editor.delete(1.0, tk.END)
        self.current_file_path = None
        self.file_path_var.set("New File")
        self.status_bar.config(text="New file created")
    
    def open_file(self):
        """Open a file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("All files", "*.*"), ("Text files", "*.txt"), ("Python files", "*.py"),
                      ("Shell scripts", "*.sh"), ("Config files", "*.conf"), ("Log files", "*.log")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(1.0, content)
                self.current_file_path = file_path
                self.file_path_var.set(file_path)
                
                # Add to recent files
                if file_path not in self.config['recent_files']:
                    self.config['recent_files'].insert(0, file_path)
                    self.config['recent_files'] = self.config['recent_files'][:10]  # Keep only 10 recent
                    self.save_config()
                    self.update_recent_files()
                
                self.status_bar.config(text=f"Opened: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")
    
    def save_file(self):
        """Save current file"""
        if self.current_file_path:
            try:
                content = self.text_editor.get(1.0, tk.END + '-1c')
                with open(self.current_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.status_bar.config(text=f"Saved: {self.current_file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
        else:
            self.save_file_as()
    
    def save_file_as(self):
        """Save file as new name"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Python files", "*.py"), 
                      ("Shell scripts", "*.sh"), ("All files", "*.*")]
        )
        if file_path:
            try:
                content = self.text_editor.get(1.0, tk.END + '-1c')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.current_file_path = file_path
                self.file_path_var.set(file_path)
                self.status_bar.config(text=f"Saved as: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
    
    def open_in_terminal_editor(self):
        """Open current file in terminal editor"""
        if not self.current_file_path:
            messagebox.showwarning("Warning", "Please save the file first!")
            return
        
        editor = self.editor_var.get()
        try:
            # Save current content first
            self.save_file()
            
            # Open in terminal editor
            if os.name == 'nt':  # Windows
                subprocess.Popen(['start', 'cmd', '/k', f'{editor} "{self.current_file_path}"'], shell=True)
            else:  # Unix-like systems
                # Try different terminal emulators
                terminal_commands = [
                    ['gnome-terminal', '--', editor, self.current_file_path],
                    ['xterm', '-e', editor, self.current_file_path],
                    ['konsole', '-e', editor, self.current_file_path],
                    ['lxterminal', '-e', editor, self.current_file_path],
                    ['xfce4-terminal', '-e', f'{editor} {self.current_file_path}'],
                ]
                
                success = False
                for cmd in terminal_commands:
                    try:
                        subprocess.Popen(cmd)
                        success = True
                        break
                    except (FileNotFoundError, OSError):
                        continue
                
                if not success:
                    # Fallback: try to open editor directly
                    try:
                        subprocess.Popen([editor, self.current_file_path])
                        success = True
                    except (FileNotFoundError, OSError):
                        pass
                
                if not success:
                    messagebox.showerror("Error", f"Could not find a suitable terminal emulator or {editor}")
                    return
            
            self.status_bar.config(text=f"Opened in {editor}: {self.current_file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open in terminal editor: {e}")
    
    def on_editor_changed(self, event):
        """Handle editor selection change"""
        self.config['preferred_editor'] = self.editor_var.get()
        self.save_config()
    
    def update_recent_files(self):
        """Update recent files list"""
        self.recent_listbox.delete(0, tk.END)
        for file_path in self.config.get('recent_files', []):
            if os.path.exists(file_path):
                self.recent_listbox.insert(tk.END, os.path.basename(file_path))
    
    def open_recent_file(self, event):
        """Open selected recent file"""
        selection = self.recent_listbox.curselection()
        if selection:
            file_path = self.config['recent_files'][selection[0]]
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.text_editor.delete(1.0, tk.END)
                    self.text_editor.insert(1.0, content)
                    self.current_file_path = file_path
                    self.file_path_var.set(file_path)
                    self.status_bar.config(text=f"Opened recent: {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open recent file: {e}")
            else:
                messagebox.showerror("Error", "File no longer exists")
                # Remove from recent files
                self.config['recent_files'].remove(file_path)
                self.save_config()
                self.update_recent_files()
    
    # Cron Manager Methods
    def refresh_cron_jobs(self):
        """Refresh cron jobs list"""
        try:
            # Clear existing items
            for item in self.cron_tree.get_children():
                self.cron_tree.delete(item)
            
            self.cron_jobs_list = []
            
            # Get current crontab
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if line and not line.startswith('#') and line != '':
                        try:
                            parts = line.split(None, 5)
                            if len(parts) >= 6:
                                schedule = ' '.join(parts[:5])
                                command = parts[5]
                                description = self.get_cron_description(schedule)
                                
                                # Store the job
                                job_data = {
                                    'line': line,
                                    'schedule': schedule,
                                    'command': command,
                                    'description': description
                                }
                                self.cron_jobs_list.append(job_data)
                                
                                # Add to tree
                                self.cron_tree.insert('', 'end', iid=str(i), text=str(i+1),
                                                    values=(schedule, 
                                                           command[:50] + '...' if len(command) > 50 else command,
                                                           description, 'Active'))
                        except Exception as e:
                            print(f"Error parsing cron line '{line}': {e}")
            
            if not self.cron_jobs_list:
                self.cron_tree.insert('', 'end', text='No Jobs', values=('', 'No cron jobs found', '', ''))
            
            # Safely update status bar
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text=f"Cron jobs refreshed - Found {len(self.cron_jobs_list)} jobs")
            
        except FileNotFoundError:
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text="crontab command not found")
            messagebox.showerror("Error", "crontab command not found. Please install cron.")
        except Exception as e:
            # If crontab is empty or user has no crontab
            if "no crontab for" in str(e).lower():
                if hasattr(self, 'status_bar'):
                    self.status_bar.config(text="No crontab found for current user")
            else:
                print(f"Error refreshing cron jobs: {e}")
                if hasattr(self, 'status_bar'):
                    self.status_bar.config(text="Error refreshing cron jobs")
    
    def get_cron_description(self, schedule):
        """Convert cron schedule to human readable description"""
        try:
            parts = schedule.split()
            if len(parts) != 5:
                return "Invalid schedule format"
            
            minute, hour, day, month, weekday = parts
            
            # Handle common patterns
            if schedule == "* * * * *":
                return "Every minute"
            elif schedule == "0 * * * *":
                return "Every hour"
            elif schedule == "0 0 * * *":
                return "Daily at midnight"
            elif schedule == "0 9 * * *":
                return "Daily at 9 AM"
            elif schedule == "0 0 * * 0":
                return "Weekly on Sunday at midnight"
            elif schedule == "0 0 1 * *":
                return "Monthly on 1st day at midnight"
            elif schedule.startswith("*/"):
                interval = schedule.split()[0][2:]
                return f"Every {interval} minutes"
            elif schedule.startswith("0 */"):
                interval = schedule.split()[1][2:]
                return f"Every {interval} hours"
            
            # Build description
            desc_parts = []
            
            # Minute
            if minute != "*":
                if minute.startswith("*/"):
                    desc_parts.append(f"every {minute[2:]} minutes")
                elif "," in minute:
                    desc_parts.append(f"at minutes {minute}")
                else:
                    desc_parts.append(f"at minute {minute}")
            
            # Hour
            if hour != "*":
                if hour.startswith("*/"):
                    desc_parts.append(f"every {hour[2:]} hours")
                elif "," in hour:
                    desc_parts.append(f"at hours {hour}")
                else:
                    desc_parts.append(f"at {hour}:00")
            
            # Day
            if day != "*":
                desc_parts.append(f"on day {day}")
            
            # Month
            if month != "*":
                months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                if month.isdigit() and 1 <= int(month) <= 12:
                    desc_parts.append(f"in {months[int(month)]}")
                else:
                    desc_parts.append(f"in month {month}")
            
            # Weekday
            if weekday != "*":
                weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                if weekday.isdigit() and 0 <= int(weekday) <= 6:
                    desc_parts.append(f"on {weekdays[int(weekday)]}")
                else:
                    desc_parts.append(f"on weekday {weekday}")
            
            return ", ".join(desc_parts) if desc_parts else "Every minute"
            
        except Exception as e:
            return f"Parse error: {str(e)}"
    
    def add_cron_job(self):
        """Add new cron job"""
        dialog = CronJobDialog(self.root, "Add Cron Job")
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            schedule, command = dialog.result
            cron_line = f"{schedule} {command}"
            
            try:
                # Get current crontab
                result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                current_crons = result.stdout if result.returncode == 0 else ""
                
                # Add new job
                if current_crons.strip():
                    new_crons = current_crons.rstrip() + '\n' + cron_line + '\n'
                else:
                    new_crons = cron_line + '\n'
                
                # Write to temporary file and install
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cron') as f:
                    f.write(new_crons)
                    temp_file = f.name
                
                result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
                os.unlink(temp_file)
                
                if result.returncode == 0:
                    self.refresh_cron_jobs()
                    self.status_bar.config(text="Cron job added successfully")
                    messagebox.showinfo("Success", "Cron job added successfully!")
                else:
                    messagebox.showerror("Error", f"Failed to add cron job: {result.stderr}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add cron job: {e}")
    
    def edit_cron_job(self):
        """Edit selected cron job"""
        selection = self.cron_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a cron job to edit")
            return
        
        if not self.cron_jobs_list:
            messagebox.showwarning("Warning", "No cron jobs to edit")
            return
        
        try:
            item_id = int(selection[0])
            if 0 <= item_id < len(self.cron_jobs_list):
                job = self.cron_jobs_list[item_id]
                
                dialog = CronJobDialog(self.root, "Edit Cron Job", job['schedule'], job['command'])
                self.root.wait_window(dialog.dialog)
                
                if dialog.result:
                    new_schedule, new_command = dialog.result
                    new_line = f"{new_schedule} {new_command}"
                    
                    # Get all cron jobs and replace the selected one
                    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        cron_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                        
                        if 0 <= item_id < len(cron_lines):
                            cron_lines[item_id] = new_line
                            
                            # Write back to crontab
                            new_crontab = '\n'.join(cron_lines) + '\n'
                            
                            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cron') as f:
                                f.write(new_crontab)
                                temp_file = f.name
                            
                            result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
                            os.unlink(temp_file)
                            
                            if result.returncode == 0:
                                self.refresh_cron_jobs()
                                self.status_bar.config(text="Cron job updated successfully")
                                messagebox.showinfo("Success", "Cron job updated successfully!")
                            else:
                                messagebox.showerror("Error", f"Failed to update cron job: {result.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit cron job: {e}")
    
    def delete_cron_job(self):
        """Delete selected cron job"""
        selection = self.cron_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a cron job to delete")
            return
        
        if not self.cron_jobs_list:
            messagebox.showwarning("Warning", "No cron jobs to delete")
            return
        
        try:
            item_id = int(selection[0])
            if 0 <= item_id < len(self.cron_jobs_list):
                job = self.cron_jobs_list[item_id]
                
                if messagebox.askyesno("Confirm Delete", 
                                     f"Are you sure you want to delete this cron job?\n\n{job['schedule']} {job['command']}"):
                    
                    # Get all cron jobs and remove the selected one
                    result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        cron_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                        
                        if 0 <= item_id < len(cron_lines):
                            # Remove the job
                            cron_lines.pop(item_id)
                            
                            if cron_lines:
                                # Write back remaining jobs
                                new_crontab = '\n'.join(cron_lines) + '\n'
                                
                                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cron') as f:
                                    f.write(new_crontab)
                                    temp_file = f.name
                                
                                result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
                                os.unlink(temp_file)
                            else:
                                # Remove all cron jobs (empty crontab)
                                result = subprocess.run(['crontab', '-r'], capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                self.refresh_cron_jobs()
                                self.status_bar.config(text="Cron job deleted successfully")
                                messagebox.showinfo("Success", "Cron job deleted successfully!")
                            else:
                                messagebox.showerror("Error", f"Failed to delete cron job: {result.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete cron job: {e}")
    
    def view_cron_logs(self):
        """View cron logs"""
        try:
            # Try common log locations
            log_files = ['/var/log/cron', '/var/log/cron.log', '/var/log/syslog']
            
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        result = subprocess.run(['tail', '-100', log_file], capture_output=True, text=True)
                        if result.returncode == 0:
                            # Filter for cron-related entries
                            lines = result.stdout.split('\n')
                            cron_lines = [line for line in lines if 'cron' in line.lower() or 'CRON' in line]
                            
                            if cron_lines:
                                LogViewerDialog(self.root, f"Cron Logs - {log_file}", '\n'.join(cron_lines))
                            else:
                                LogViewerDialog(self.root, f"System Logs - {log_file}", result.stdout)
                            return
                    except PermissionError:
                        continue
            
            # Try journalctl for systemd systems
            try:
                result = subprocess.run(['journalctl', '-u', 'cron', '-n', '50'], capture_output=True, text=True)
                if result.returncode == 0:
                    LogViewerDialog(self.root, "Cron Logs - journalctl", result.stdout)
                    return
            except FileNotFoundError:
                pass
            
            messagebox.showinfo("Info", "No accessible cron logs found.\n\nTried locations:\n- /var/log/cron\n- /var/log/cron.log\n- /var/log/syslog\n- journalctl")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view cron logs: {e}")
    
    def on_cron_select(self, event):
        """Handle cron job selection"""
        selection = self.cron_tree.selection()
        if selection and self.cron_jobs_list:
            try:
                item_id = int(selection[0])
                if 0 <= item_id < len(self.cron_jobs_list):
                    job = self.cron_jobs_list[item_id]
                    
                    details = f"Full Command Line:\n{job['line']}\n\n"
                    details += f"Schedule: {job['schedule']}\n"
                    details += f"Command: {job['command']}\n"
                    details += f"Description: {job['description']}\n"
                    details += f"Status: Active\n\n"
                    
                    # Add schedule breakdown
                    parts = job['schedule'].split()
                    if len(parts) == 5:
                        details += "Schedule Breakdown:\n"
                        details += f"  Minute: {parts[0]} (0-59)\n"
                        details += f"  Hour: {parts[1]} (0-23)\n"
                        details += f"  Day: {parts[2]} (1-31)\n"
                        details += f"  Month: {parts[3]} (1-12)\n"
                        details += f"  Weekday: {parts[4]} (0-6, 0=Sunday)\n"
                    
                    self.cron_details.delete(1.0, tk.END)
                    self.cron_details.insert(1.0, details)
            except (ValueError, IndexError):
                pass
    
    # SSH Manager Methods
    def load_ssh_connections(self):
        """Load saved SSH connections"""
        self.ssh_listbox.delete(0, tk.END)
        for conn in self.config.get('ssh_connections', []):
            display_name = f"{conn['name']} ({conn['user']}@{conn['host']}:{conn.get('port', 22)})"
            self.ssh_listbox.insert(tk.END, display_name)
    
    def add_ssh_connection(self):
        """Add new SSH connection"""
        dialog = SSHConnectionDialog(self.root, "Add SSH Connection")
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            if 'ssh_connections' not in self.config:
                self.config['ssh_connections'] = []
            
            self.config['ssh_connections'].append(dialog.result)
            self.save_config()
            self.load_ssh_connections()
            self.status_bar.config(text="SSH connection added successfully")
    
    def edit_ssh_connection(self):
        """Edit selected SSH connection"""
        selection = self.ssh_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a connection to edit")
            return
        
        if not self.config.get('ssh_connections'):
            messagebox.showwarning("Warning", "No connections to edit")
            return
        
        conn_data = self.config['ssh_connections'][selection[0]]
        dialog = SSHConnectionDialog(self.root, "Edit SSH Connection", conn_data)
        self.root.wait_window(dialog.dialog)
        
        if dialog.result:
            self.config['ssh_connections'][selection[0]] = dialog.result
            self.save_config()
            self.load_ssh_connections()
            self.status_bar.config(text="SSH connection updated successfully")
    
    def delete_ssh_connection(self):
        """Delete selected SSH connection"""
        selection = self.ssh_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a connection to delete")
            return
        
        if not self.config.get('ssh_connections'):
            messagebox.showwarning("Warning", "No connections to delete")
            return
        
        conn = self.config['ssh_connections'][selection[0]]
        if messagebox.askyesno("Confirm Delete", f"Delete connection '{conn['name']}'?"):
            del self.config['ssh_connections'][selection[0]]
            self.save_config()
            self.load_ssh_connections()
            self.status_bar.config(text="SSH connection deleted successfully")
    
    def connect_ssh(self, event=None):
        """Connect to selected SSH server"""
        selection = self.ssh_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a connection first")
            return
        
        if not self.config.get('ssh_connections'):
            messagebox.showwarning("Warning", "No saved connections available")
            return
        
        conn = self.config['ssh_connections'][selection[0]]
        self.start_ssh_session(conn['host'], conn['user'], conn.get('port', 22), conn.get('key_file'))
    
    def quick_ssh_connect(self):
        """Quick SSH connection"""
        host = self.quick_host.get().strip()
        user = self.quick_user.get().strip()
        
        if not host or not user:
            messagebox.showwarning("Warning", "Please enter both host and user")
            return
        
        self.start_ssh_session(host, user)
    
    def start_ssh_session(self, host, user, port=22, key_file=None):
        """Start SSH session"""
        try:
            self.ssh_output.insert(tk.END, f"Connecting to {user}@{host}:{port}...\n")
            self.ssh_output.see(tk.END)
            
            # Build SSH command
            cmd = ['ssh']
            if key_file and os.path.exists(key_file):
                cmd.extend(['-i', key_file])
            if port != 22:
                cmd.extend(['-p', str(port)])
            
            # Add SSH options for better interaction
            cmd.extend(['-o', 'StrictHostKeyChecking=no'])
            cmd.extend(['-o', 'UserKnownHostsFile=/dev/null'])
            cmd.extend(['-t'])  # Force pseudo-terminal allocation
            
            cmd.append(f'{user}@{host}')
            
            # Start SSH in a new terminal window for full interactivity
            if os.name == 'nt':  # Windows
                subprocess.Popen(['start', 'cmd', '/k'] + cmd, shell=True)
                self.ssh_output.insert(tk.END, f"SSH session opened in new window\n")
            else:  # Unix-like systems
                terminal_commands = [
                    ['gnome-terminal', '--'] + cmd,
                    ['xterm', '-e'] + cmd,
                    ['konsole', '-e'] + cmd,
                    ['lxterminal', '-e'] + cmd,
                    ['xfce4-terminal', '-e', ' '.join(cmd)],
                ]
                
                success = False
                for term_cmd in terminal_commands:
                    try:
                        subprocess.Popen(term_cmd)
                        success = True
                        break
                    except (FileNotFoundError, OSError):
                        continue
                
                if success:
                    self.ssh_output.insert(tk.END, f"SSH session opened in new terminal window\n")
                else:
                    # Try to start a simple SSH session in the current process
                    self.ssh_output.insert(tk.END, f"Could not open terminal window, trying embedded connection...\n")
                    self.start_embedded_ssh(cmd)
            
            self.status_bar.config(text=f"SSH connection initiated to {user}@{host}")
            
        except Exception as e:
            self.ssh_output.insert(tk.END, f"Error: Failed to start SSH session: {e}\n")
            messagebox.showerror("Error", f"Failed to start SSH session: {e}")
    
    def start_embedded_ssh(self, cmd):
        """Start SSH session within the application"""
        try:
            self.current_ssh_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0
            )
            
            # Start thread to read SSH output
            threading.Thread(target=self.read_ssh_output, daemon=True).start()
            
            self.ssh_output.insert(tk.END, "Embedded SSH session started\n")
            
        except Exception as e:
            self.ssh_output.insert(tk.END, f"Failed to start embedded SSH: {e}\n")
    
    def read_ssh_output(self):
        """Read SSH output in a separate thread"""
        if not self.current_ssh_process:
            return
        
        try:
            while self.current_ssh_process and self.current_ssh_process.poll() is None:
                output = self.current_ssh_process.stdout.readline()
                if output:
                    self.root.after(0, lambda text=output: self.ssh_output.insert(tk.END, text))
                    self.root.after(0, lambda: self.ssh_output.see(tk.END))
                else:
                    break
        except Exception as e:
            self.root.after(0, lambda: self.ssh_output.insert(tk.END, f"SSH read error: {e}\n"))
    
    def send_ssh_command(self, event=None):
        """Send command to SSH session"""
        command = self.ssh_input.get().strip()
        if command:
            self.ssh_output.insert(tk.END, f"$ {command}\n")
            self.ssh_input.delete(0, tk.END)
            
            # Add to history
            if command not in self.ssh_history:
                self.ssh_history.append(command)
            self.ssh_history_index = len(self.ssh_history)
            
            if self.current_ssh_process and self.current_ssh_process.poll() is None:
                try:
                    self.current_ssh_process.stdin.write(command + '\n')
                    self.current_ssh_process.stdin.flush()
                except Exception as e:
                    self.ssh_output.insert(tk.END, f"Error sending command: {e}\n")
            else:
                self.ssh_output.insert(tk.END, "No active SSH connection\n")
            
            self.ssh_output.see(tk.END)
    
    def disconnect_ssh(self):
        """Disconnect SSH session"""
        if self.current_ssh_process:
            try:
                self.current_ssh_process.terminate()
                self.current_ssh_process = None
                self.ssh_output.insert(tk.END, "SSH connection terminated\n")
                self.status_bar.config(text="SSH disconnected")
            except Exception as e:
                self.ssh_output.insert(tk.END, f"Error disconnecting: {e}\n")
        else:
            self.ssh_output.insert(tk.END, "No active SSH connection\n")
    
    def clear_ssh_output(self):
        """Clear SSH output"""
        self.ssh_output.delete(1.0, tk.END)
    
    def ssh_history_up(self, event):
        """Navigate SSH command history up"""
        if self.ssh_history and self.ssh_history_index > 0:
            self.ssh_history_index -= 1
            self.ssh_input.delete(0, tk.END)
            self.ssh_input.insert(0, self.ssh_history[self.ssh_history_index])
    
    def ssh_history_down(self, event):
        """Navigate SSH command history down"""
        if self.ssh_history and self.ssh_history_index < len(self.ssh_history) - 1:
            self.ssh_history_index += 1
            self.ssh_input.delete(0, tk.END)
            self.ssh_input.insert(0, self.ssh_history[self.ssh_history_index])
        elif self.ssh_history_index >= len(self.ssh_history) - 1:
            self.ssh_history_index = len(self.ssh_history)
            self.ssh_input.delete(0, tk.END)
    
    # Terminal Methods
    def clear_terminal(self):
        """Clear terminal output"""
        self.terminal_output.delete(1.0, tk.END)
        self.status_bar.config(text="Terminal cleared")
    
    def stop_terminal_process(self):
        """Stop current terminal process"""
        # In a more complete implementation, this would track and terminate running processes
        self.status_bar.config(text="Process stop requested")
    
    def browse_working_dir(self):
        """Browse for working directory"""
        directory = filedialog.askdirectory(initialdir=self.working_dir.get())
        if directory:
            self.working_dir.delete(0, tk.END)
            self.working_dir.insert(0, directory)
    
    def set_working_dir(self):
        """Set working directory"""
        directory = self.working_dir.get().strip()
        if directory and os.path.isdir(directory):
            try:
                os.chdir(directory)
                self.terminal_output.insert(tk.END, f"Changed working directory to: {directory}\n")
                self.status_bar.config(text=f"Working directory: {directory}")
            except Exception as e:
                self.terminal_output.insert(tk.END, f"Error changing directory: {e}\n")
                messagebox.showerror("Error", f"Failed to change directory: {e}")
        else:
            messagebox.showerror("Error", "Invalid directory path")
    
    def execute_terminal_command(self, event=None):
        """Execute terminal command"""
        command = self.terminal_input.get().strip()
        if not command:
            return
        
        # Add to history
        if command not in self.command_history:
            self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # Display command
        working_dir = self.working_dir.get() or os.getcwd()
        self.terminal_output.insert(tk.END, f"{working_dir}$ {command}\n")
        self.terminal_input.delete(0, tk.END)
        
        # Execute command in thread to prevent GUI blocking
        threading.Thread(target=self.run_command, args=(command,), daemon=True).start()
    
    def run_command(self, command):
        """Run command in subprocess"""
        try:
            working_dir = self.working_dir.get() or os.getcwd()
            
            # Handle built-in commands
            if command == 'clear':
                self.root.after(0, self.clear_terminal)
                return
            elif command.startswith('cd '):
                new_dir = command[3:].strip()
                if new_dir == '~':
                    new_dir = str(Path.home())
                elif new_dir.startswith('~/'):
                    new_dir = str(Path.home() / new_dir[2:])
                elif not os.path.isabs(new_dir):
                    new_dir = os.path.join(working_dir, new_dir)
                
                if os.path.isdir(new_dir):
                    os.chdir(new_dir)
                    self.working_dir.delete(0, tk.END)
                    self.working_dir.insert(0, os.getcwd())
                    self.root.after(0, lambda: self.terminal_output.insert(tk.END, f"Changed to {os.getcwd()}\n"))
                else:
                    self.root.after(0, lambda: self.terminal_output.insert(tk.END, f"Directory not found: {new_dir}\n"))
                return
            elif command == 'pwd':
                self.root.after(0, lambda: self.terminal_output.insert(tk.END, f"{os.getcwd()}\n"))
                return
            elif command in ['exit', 'quit']:
                self.root.after(0, lambda: self.terminal_output.insert(tk.END, "Use the GUI to exit the application\n"))
                return
            
            # Run external command
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=working_dir,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.root.after(0, lambda line=output: self.terminal_output.insert(tk.END, line))
                    self.root.after(0, lambda: self.terminal_output.see(tk.END))
            
            return_code = process.poll()
            if return_code != 0:
                self.root.after(0, lambda: self.terminal_output.insert(tk.END, f"Command exited with code {return_code}\n"))
            
        except Exception as e:
            self.root.after(0, lambda: self.terminal_output.insert(tk.END, f"Error: {e}\n"))
    
    def terminal_history_up(self, event):
        """Navigate command history up"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.terminal_input.delete(0, tk.END)
            self.terminal_input.insert(0, self.command_history[self.history_index])
    
    def terminal_history_down(self, event):
        """Navigate command history down"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.terminal_input.delete(0, tk.END)
            self.terminal_input.insert(0, self.command_history[self.history_index])
        elif self.history_index >= len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.terminal_input.delete(0, tk.END)
    
    # System Monitor Methods
    def refresh_system_info(self):
        """Refresh system information"""
        try:
            info = []
            
            # System info
            info.append(f"System Information - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            info.append("=" * 50)
            
            # Platform info
            import platform
            info.append(f"System: {platform.system()}")
            info.append(f"Node: {platform.node()}")
            info.append(f"Release: {platform.release()}")
            info.append(f"Version: {platform.version()}")
            info.append(f"Machine: {platform.machine()}")
            info.append(f"Processor: {platform.processor()}")
            
            # Uptime (Unix-like systems)
            try:
                if os.name != 'nt' and os.path.exists('/proc/uptime'):
                    with open('/proc/uptime', 'r') as f:
                        uptime_seconds = float(f.read().split()[0])
                        uptime_hours = int(uptime_seconds // 3600)
                        uptime_minutes = int((uptime_seconds % 3600) // 60)
                        info.append(f"Uptime: {uptime_hours}h {uptime_minutes}m")
            except:
                pass
            
            info.append("")
            
            # Memory info
            try:
                if os.name != 'nt':
                    result = subprocess.run(['free', '-h'], capture_output=True, text=True)
                    if result.returncode == 0:
                        info.append("Memory Information:")
                        info.extend(result.stdout.split('\n'))
                        info.append("")
                else:
                    # Windows memory info
                    result = subprocess.run(['wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/format:list'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        info.append("Memory Information:")
                        info.extend([line for line in result.stdout.split('\n') if '=' in line])
                        info.append("")
            except:
                pass
            
            # Disk usage
            try:
                if os.name != 'nt':
                    result = subprocess.run(['df', '-h'], capture_output=True, text=True)
                else:
                    result = subprocess.run(['wmic', 'logicaldisk', 'get', 'size,freespace,caption'], capture_output=True, text=True)
                
                if result.returncode == 0:
                    info.append("Disk Usage:")
                    info.extend(result.stdout.split('\n'))
                    info.append("")
            except:
                pass
            
            # Load average (Unix-like)
            try:
                if os.name != 'nt' and os.path.exists('/proc/loadavg'):
                    with open('/proc/loadavg', 'r') as f:
                        load_avg = f.read().strip().split()[:3]
                        info.append(f"Load Average: {' '.join(load_avg)} (1m 5m 15m)")
                        info.append("")
            except:
                pass
            
            # Network interfaces
            try:
                if os.name != 'nt':
                    result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
                    if result.returncode == 0:
                        info.append("Network Interfaces:")
                        lines = result.stdout.split('\n')[:20]  # Limit output
                        info.extend(lines)
                else:
                    result = subprocess.run(['ipconfig'], capture_output=True, text=True)
                    if result.returncode == 0:
                        info.append("Network Configuration:")
                        lines = result.stdout.split('\n')[:20]  # Limit output
                        info.extend(lines)
            except:
                pass
            
            # Update GUI
            self.system_info.delete(1.0, tk.END)
            self.system_info.insert(1.0, '\n'.join(info))
            
            # Refresh processes
            self.refresh_processes()
            
            # Update status bar safely
            if hasattr(self, 'status_bar'):
                self.status_bar.config(text=f"System info updated at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.system_info.delete(1.0, tk.END)
            self.system_info.insert(1.0, f"Error refreshing system info: {e}")
    
    def refresh_processes(self):
        """Refresh process list"""
        try:
            # Clear existing items
            for item in self.process_tree.get_children():
                self.process_tree.delete(item)
            
            if os.name != 'nt':
                # Unix-like systems
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    for line in lines[:100]:  # Limit to first 100 processes
                        parts = line.split(None, 10)
                        if len(parts) >= 11:
                            user, pid, cpu, mem = parts[0], parts[1], parts[2], parts[3]
                            command = parts[10][:50] + '...' if len(parts[10]) > 50 else parts[10]
                            
                            self.process_tree.insert('', 'end', values=(pid, command, cpu, mem, user))
            else:
                # Windows
                result = subprocess.run(['tasklist', '/fo', 'csv'], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    for line in lines[:100]:  # Limit to first 100 processes
                        parts = [p.strip('"') for p in line.split('","')]
                        if len(parts) >= 5:
                            name, pid, session, mem = parts[0], parts[1], parts[2], parts[4]
                            self.process_tree.insert('', 'end', values=(pid, name, 'N/A', mem, 'N/A'))
            
        except Exception as e:
            print(f"Error refreshing processes: {e}")
    
    def kill_process(self):
        """Kill selected process"""
        selection = self.process_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a process to kill")
            return
        
        item = self.process_tree.item(selection[0])
        pid = item['values'][0]
        process_name = item['values'][1]
        
        if messagebox.askyesno("Confirm", f"Kill process {pid} ({process_name})?"):
            try:
                if os.name != 'nt':
                    subprocess.run(['kill', pid], check=True)
                else:
                    subprocess.run(['taskkill', '/PID', pid, '/F'], check=True)
                
                self.refresh_processes()
                self.status_bar.config(text=f"Process {pid} terminated")
                messagebox.showinfo("Success", f"Process {pid} terminated successfully")
                
            except subprocess.CalledProcessError:
                if messagebox.askyesno("Force Kill", f"Normal kill failed. Force kill process {pid}?"):
                    try:
                        if os.name != 'nt':
                            subprocess.run(['kill', '-9', pid], check=True)
                        else:
                            subprocess.run(['taskkill', '/PID', pid, '/F'], check=True)
                        
                        self.refresh_processes()
                        self.status_bar.config(text=f"Process {pid} force killed")
                        messagebox.showinfo("Success", f"Process {pid} force killed")
                        
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to kill process: {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to kill process: {e}")
    
    def view_system_logs(self):
        """View system logs"""
        try:
            log_files = []
            
            if os.name != 'nt':
                # Unix-like systems
                log_files = ['/var/log/syslog', '/var/log/messages', '/var/log/kern.log', '/var/log/dmesg']
                
                for log_file in log_files:
                    if os.path.exists(log_file):
                        try:
                            result = subprocess.run(['tail', '-200', log_file], capture_output=True, text=True)
                            if result.returncode == 0:
                                LogViewerDialog(self.root, f"System Logs - {log_file}", result.stdout)
                                return
                        except PermissionError:
                            continue
                
                # Try journalctl for systemd systems
                try:
                    result = subprocess.run(['journalctl', '-n', '100'], capture_output=True, text=True)
                    if result.returncode == 0:
                        LogViewerDialog(self.root, "System Logs - journalctl", result.stdout)
                        return
                except FileNotFoundError:
                    pass
            else:
                # Windows Event Log
                try:
                    result = subprocess.run(['wevtutil', 'qe', 'System', '/f:text', '/c:50'], capture_output=True, text=True)
                    if result.returncode == 0:
                        LogViewerDialog(self.root, "System Logs - Windows Event Log", result.stdout)
                        return
                except:
                    pass
            
            messagebox.showinfo("Info", "No accessible system logs found or insufficient permissions.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view system logs: {e}")
    
    def toggle_auto_refresh(self):
        """Toggle auto refresh"""
        if not self.auto_refresh_var.get():
            if self.auto_refresh_job:
                self.root.after_cancel(self.auto_refresh_job)
                self.auto_refresh_job = None
    
    def schedule_auto_refresh(self):
        """Schedule automatic refresh of system info"""
        if self.auto_refresh_var.get():
            self.auto_refresh_job = self.root.after(5000, lambda: (self.refresh_system_info(), self.schedule_auto_refresh()))
        else:
            self.auto_refresh_job = self.root.after(5000, self.schedule_auto_refresh)


# Dialog Classes
class CronJobDialog:
    def __init__(self, parent, title, schedule="", command=""):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Command entry
        cmd_frame = ttk.LabelFrame(main_frame, text="Command to Execute")
        cmd_frame.pack(fill='x', pady=(0, 10))
        
        self.command_entry = scrolledtext.ScrolledText(cmd_frame, height=4, wrap=tk.WORD)
        self.command_entry.pack(fill='x', padx=10, pady=10)
        if command:
            self.command_entry.insert(1.0, command)
        
        # Examples
        examples_text = "Examples:\n• python3 /home/user/backup.py\n• rsync -av /src/ /backup/\n• /usr/bin/cleanup.sh --log"
        ttk.Label(cmd_frame, text=examples_text, font=('TkDefaultFont', 8)).pack(anchor='w', padx=10, pady=(0, 10))
        
        # Schedule selection
        schedule_frame = ttk.LabelFrame(main_frame, text="Schedule")
        schedule_frame.pack(fill='both', expand=True, pady=5)
        
        # Preset schedules
        preset_frame = ttk.Frame(schedule_frame)
        preset_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(preset_frame, text="Quick Presets:", font=('TkDefaultFont', 9, 'bold')).pack(anchor='w')
        
        self.preset_var = tk.StringVar()
        presets = [
            ("Every minute", "* * * * *"),
            ("Every 5 minutes", "*/5 * * * *"),
            ("Every 15 minutes", "*/15 * * * *"),
            ("Every 30 minutes", "*/30 * * * *"),
            ("Every hour", "0 * * * *"),
            ("Every 2 hours", "0 */2 * * *"),
            ("Every 6 hours", "0 */6 * * *"),
            ("Daily at midnight", "0 0 * * *"),
            ("Daily at 6 AM", "0 6 * * *"),
            ("Daily at 9 AM", "0 9 * * *"),
            ("Daily at 6 PM", "0 18 * * *"),
            ("Weekly (Monday midnight)", "0 0 * * 1"),
            ("Weekly (Sunday 2 AM)", "0 2 * * 0"),
            ("Monthly (1st at midnight)", "0 0 1 * *"),
            ("Custom", "custom")
        ]
        
        # Create preset buttons in a grid
        preset_grid = ttk.Frame(preset_frame)
        preset_grid.pack(fill='x', pady=5)
        
        row, col = 0, 0
        for text, value in presets:
            ttk.Radiobutton(preset_grid, text=text, variable=self.preset_var, 
                           value=value, command=self.on_preset_change).grid(row=row, column=col, sticky='w', padx=5, pady=1)
            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1
        
        # Custom schedule
        custom_frame = ttk.LabelFrame(schedule_frame, text="Custom Schedule")
        custom_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(custom_frame, text="Cron Format: minute hour day month weekday").pack(anchor='w', padx=5, pady=(5,0))
        
        self.schedule_entry = ttk.Entry(custom_frame, font=('Consolas', 10))
        self.schedule_entry.pack(fill='x', padx=5, pady=5)
        
        if schedule:
            self.schedule_entry.insert(0, schedule)
            self.preset_var.set("custom")
        else:
            self.preset_var.set("0 0 * * *")
            self.schedule_entry.insert(0, "0 0 * * *")
        
        # Help text
        help_frame = ttk.Frame(custom_frame)
        help_frame.pack(fill='x', padx=5, pady=5)
        
        help_text = """Format Help:
• * = any value    • */N = every N units    • N-M = range    • N,M,O = list
• minute: 0-59    • hour: 0-23    • day: 1-31    • month: 1-12    • weekday: 0-6 (0=Sunday)"""
        
        ttk.Label(help_frame, text=help_text, font=('TkDefaultFont', 8), 
                 foreground='#666666', justify='left').pack(anchor='w')
        
        # Preview
        self.preview_frame = ttk.LabelFrame(main_frame, text="Schedule Preview")
        self.preview_frame.pack(fill='x', pady=5)
        
        self.preview_label = ttk.Label(self.preview_frame, text="", wraplength=500)
        self.preview_label.pack(anchor='w', padx=10, pady=5)
        
        # Bind events for live preview
        self.schedule_entry.bind('<KeyRelease>', self.update_preview)
        self.preset_var.trace('w', self.update_preview)
        
        # Update initial preview
        self.update_preview()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side='right')
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self.ok_clicked())
        self.dialog.bind('<Escape>', lambda e: self.cancel_clicked())
        
        # Focus on command entry
        self.command_entry.focus()
    
    def on_preset_change(self):
        """Handle preset selection change"""
        preset = self.preset_var.get()
        if preset != "custom":
            self.schedule_entry.delete(0, tk.END)
            self.schedule_entry.insert(0, preset)
        self.update_preview()
    
    def update_preview(self, *args):
        """Update schedule preview"""
        try:
            schedule = self.schedule_entry.get().strip()
            if not schedule:
                self.preview_label.config(text="Enter a schedule to see preview")
                return
            
            # Basic validation
            parts = schedule.split()
            if len(parts) != 5:
                self.preview_label.config(text="Invalid format: Must have 5 fields (minute hour day month weekday)")
                return
            
            # Generate human-readable description
            description = self.get_cron_description(schedule)
            self.preview_label.config(text=f"This job will run: {description}")
            
        except Exception as e:
            self.preview_label.config(text=f"Preview error: {e}")
    
    def get_cron_description(self, schedule):
        """Generate human-readable description of cron schedule"""
        try:
            parts = schedule.split()
            if len(parts) != 5:
                return "Invalid schedule format"
            
            minute, hour, day, month, weekday = parts
            
            # Handle common patterns
            if schedule == "* * * * *":
                return "Every minute"
            elif schedule == "0 * * * *":
                return "Every hour"
            elif schedule == "0 0 * * *":
                return "Daily at midnight (00:00)"
            elif schedule == "0 9 * * *":
                return "Daily at 9:00 AM"
            elif schedule == "0 18 * * *":
                return "Daily at 6:00 PM"
            elif schedule == "0 0 * * 0":
                return "Weekly on Sunday at midnight"
            elif schedule == "0 0 * * 1":
                return "Weekly on Monday at midnight"
            elif schedule == "0 0 1 * *":
                return "Monthly on the 1st day at midnight"
            elif schedule.startswith("*/"):
                interval = schedule.split()[0][2:]
                return f"Every {interval} minutes"
            elif schedule.startswith("0 */"):
                interval = schedule.split()[1][2:]
                return f"Every {interval} hours"
            
            # Build detailed description
            desc_parts = []
            
            # Time description
            if minute == "*" and hour == "*":
                desc_parts.append("every minute")
            elif minute != "*" and hour == "*":
                if minute.startswith("*/"):
                    desc_parts.append(f"every {minute[2:]} minutes")
                else:
                    desc_parts.append(f"at minute {minute} of every hour")
            elif minute == "*" and hour != "*":
                if hour.startswith("*/"):
                    desc_parts.append(f"every minute of every {hour[2:]} hours")
                else:
                    desc_parts.append(f"every minute at hour {hour}")
            else:
                # Both minute and hour specified
                if minute.startswith("*/") or hour.startswith("*/"):
                    if minute.startswith("*/"):
                        desc_parts.append(f"every {minute[2:]} minutes")
                    else:
                        desc_parts.append(f"at minute {minute}")
                    
                    if hour.startswith("*/"):
                        desc_parts.append(f"every {hour[2:]} hours")
                    else:
                        desc_parts.append(f"at hour {hour}")
                else:
                    hour_int = int(hour) if hour.isdigit() else 0
                    minute_int = int(minute) if minute.isdigit() else 0
                    time_str = f"{hour_int:02d}:{minute_int:02d}"
                    desc_parts.append(f"at {time_str}")
            
            # Date/day description
            date_parts = []
            
            if day != "*":
                date_parts.append(f"on day {day}")
            
            if month != "*":
                months = ["", "January", "February", "March", "April", "May", "June",
                         "July", "August", "September", "October", "November", "December"]
                if month.isdigit() and 1 <= int(month) <= 12:
                    date_parts.append(f"in {months[int(month)]}")
                else:
                    date_parts.append(f"in month {month}")
            
            if weekday != "*":
                weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                if weekday.isdigit() and 0 <= int(weekday) <= 6:
                    date_parts.append(f"on {weekdays[int(weekday)]}")
                else:
                    date_parts.append(f"on weekday {weekday}")
            
            if date_parts:
                desc_parts.extend(date_parts)
            
            if not desc_parts:
                return "Every minute"
            
            return " ".join(desc_parts)
            
        except Exception as e:
            return f"Error parsing schedule: {e}"
    
    def ok_clicked(self):
        """Handle OK button click"""
        command = self.command_entry.get(1.0, tk.END).strip()
        schedule = self.schedule_entry.get().strip()
        
        if not command:
            messagebox.showerror("Error", "Command cannot be empty")
            self.command_entry.focus()
            return
        
        if not schedule:
            messagebox.showerror("Error", "Schedule cannot be empty")
            self.schedule_entry.focus()
            return
        
        # Basic validation
        parts = schedule.split()
        if len(parts) != 5:
            messagebox.showerror("Error", "Schedule must have exactly 5 fields:\nminute hour day month weekday")
            self.schedule_entry.focus()
            return
        
        # Validate each field
        try:
            minute, hour, day, month, weekday = parts
            
            def validate_field(value, min_val, max_val, field_name):
                if value == "*":
                    return True
                if value.startswith("*/"):
                    interval = int(value[2:])
                    return min_val <= interval <= max_val
                if "," in value:
                    for v in value.split(","):
                        if not (min_val <= int(v.strip()) <= max_val):
                            return False
                    return True
                if "-" in value:
                    start, end = value.split("-")
                    return min_val <= int(start) <= int(end) <= max_val
                return min_val <= int(value) <= max_val
            
            if not validate_field(minute, 0, 59, "minute"):
                raise ValueError("Minute must be 0-59")
            if not validate_field(hour, 0, 23, "hour"):
                raise ValueError("Hour must be 0-23")
            if not validate_field(day, 1, 31, "day"):
                raise ValueError("Day must be 1-31")
            if not validate_field(month, 1, 12, "month"):
                raise ValueError("Month must be 1-12")
            if not validate_field(weekday, 0, 6, "weekday"):
                raise ValueError("Weekday must be 0-6 (0=Sunday)")
                
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid schedule: {e}")
            self.schedule_entry.focus()
            return
        
        self.result = (schedule, command)
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()


class SSHConnectionDialog:
    def __init__(self, parent, title, connection_data=None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Connection fields
        fields_frame = ttk.LabelFrame(main_frame, text="Connection Details")
        fields_frame.pack(fill='x', pady=(0, 10))
        
        # Name
        ttk.Label(fields_frame, text="Connection Name *:").pack(anchor='w', padx=10, pady=(10, 0))
        self.name_entry = ttk.Entry(fields_frame)
        self.name_entry.pack(fill='x', padx=10, pady=(0, 10))
        
        # Host
        ttk.Label(fields_frame, text="Host/IP Address *:").pack(anchor='w', padx=10, pady=(0, 0))
        self.host_entry = ttk.Entry(fields_frame)
        self.host_entry.pack(fill='x', padx=10, pady=(0, 10))
        
        # User
        ttk.Label(fields_frame, text="Username *:").pack(anchor='w', padx=10, pady=(0, 0))
        self.user_entry = ttk.Entry(fields_frame)
        self.user_entry.pack(fill='x', padx=10, pady=(0, 10))
        
        # Port
        ttk.Label(fields_frame, text="Port:").pack(anchor='w', padx=10, pady=(0, 0))
        self.port_entry = ttk.Entry(fields_frame)
        self.port_entry.pack(fill='x', padx=10, pady=(0, 10))
        self.port_entry.insert(0, "22")
        
        # Key file
        ttk.Label(fields_frame, text="SSH Key File (optional):").pack(anchor='w', padx=10, pady=(0, 0))
        key_frame = ttk.Frame(fields_frame)
        key_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        self.key_entry = ttk.Entry(key_frame)
        self.key_entry.pack(side='left', fill='x', expand=True)
        ttk.Button(key_frame, text="Browse", command=self.browse_key_file).pack(side='right', padx=(5, 0))
        
        # Fill fields if editing
        if connection_data:
            self.name_entry.insert(0, connection_data.get('name', ''))
            self.host_entry.insert(0, connection_data.get('host', ''))
            self.user_entry.insert(0, connection_data.get('user', ''))
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, str(connection_data.get('port', 22)))
            if connection_data.get('key_file'):
                self.key_entry.insert(0, connection_data.get('key_file', ''))
        
        # Examples
        examples_frame = ttk.LabelFrame(main_frame, text="Examples")
        examples_frame.pack(fill='x', pady=5)
        
        examples_text = """• Name: Production Server
• Host: prod.example.com or 192.168.1.100
• User: admin, root, ubuntu, ec2-user
• Port: 22 (default), 2222, 2200
• Key: /home/user/.ssh/id_rsa, ~/.ssh/mykey.pem"""
        
        ttk.Label(examples_frame, text=examples_text, font=('TkDefaultFont', 8), 
                 justify='left').pack(anchor='w', padx=10, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(button_frame, text="Test Connection", command=self.test_connection).pack(side='left')
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel_clicked).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=self.ok_clicked).pack(side='right')
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self.ok_clicked())
        self.dialog.bind('<Escape>', lambda e: self.cancel_clicked())
        
        # Focus on name entry
        self.name_entry.focus()
    
    def browse_key_file(self):
        """Browse for SSH key file"""
        file_path = filedialog.askopenfilename(
            title="Select SSH Key File",
            initialdir=str(Path.home() / '.ssh'),
            filetypes=[("Key files", "*.pem *.key *.pub"), ("All files", "*.*")]
        )
        if file_path:
            self.key_entry.delete(0, tk.END)
            self.key_entry.insert(0, file_path)
    
    def test_connection(self):
        """Test the SSH connection"""
        host = self.host_entry.get().strip()
        user = self.user_entry.get().strip()
        port = self.port_entry.get().strip()
        key_file = self.key_entry.get().strip()
        
        if not host or not user:
            messagebox.showerror("Error", "Host and User are required for testing")
            return
        
        try:
            port_num = int(port) if port else 22
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return
        
        # Test connection
        cmd = ['ssh', '-o', 'ConnectTimeout=10', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=no']
        
        if key_file and os.path.exists(key_file):
            cmd.extend(['-i', key_file])
        
        if port_num != 22:
            cmd.extend(['-p', str(port_num)])
        
        cmd.extend([f'{user}@{host}', 'echo', 'Connection test successful'])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                messagebox.showinfo("Success", "SSH connection test successful!")
            else:
                messagebox.showerror("Connection Failed", 
                                   f"Connection test failed:\n{result.stderr}\n\nThis might be due to:\n"
                                   + "• Host unreachable\n• Wrong credentials\n• Firewall blocking\n• SSH key issues")
                
        except subprocess.TimeoutExpired:
            messagebox.showerror("Timeout", "Connection test timed out. Host may be unreachable.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to test connection: {e}")
    
    def ok_clicked(self):
        """Handle OK button click"""
        name = self.name_entry.get().strip()
        host = self.host_entry.get().strip()
        user = self.user_entry.get().strip()
        port = self.port_entry.get().strip()
        key_file = self.key_entry.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Connection name is required")
            self.name_entry.focus()
            return
            
        if not host:
            messagebox.showerror("Error", "Host is required")
            self.host_entry.focus()
            return
            
        if not user:
            messagebox.showerror("Error", "Username is required")
            self.user_entry.focus()
            return
        
        try:
            port_num = int(port) if port else 22
            if not (1 <= port_num <= 65535):
                raise ValueError("Port must be between 1 and 65535")
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid port: {e}")
            self.port_entry.focus()
            return
        
        if key_file and not os.path.exists(key_file):
            if not messagebox.askyesno("Warning", 
                                     f"SSH key file does not exist:\n{key_file}\n\nSave connection anyway?"):
                return
        
        self.result = {
            'name': name,
            'host': host,
            'user': user,
            'port': port_num,
            'key_file': key_file if key_file else None
        }
        self.dialog.destroy()
    
    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()


class LogViewerDialog:
    def __init__(self, parent, title, content):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("900x700")
        self.dialog.transient(parent)
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill='x', pady=(0, 5))
        
        ttk.Button(toolbar, text="Refresh", command=lambda: self.refresh_log(title, content)).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save to File", command=self.save_log).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Clear", command=self.clear_log).pack(side='left', padx=2)
        
        # Search
        ttk.Label(toolbar, text="Search:").pack(side='right', padx=(10, 5))
        self.search_entry = ttk.Entry(toolbar, width=20)
        self.search_entry.pack(side='right', padx=2)
        self.search_entry.bind('<Return>', self.search_log)
        ttk.Button(toolbar, text="Find", command=self.search_log).pack(side='right', padx=2)
        
        # Log content
        self.log_text = scrolledtext.ScrolledText(main_frame, 
                                                 bg='#1e1e1e', fg='#d4d4d4',
                                                 font=('Consolas', 9),
                                                 wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True)
        self.log_text.insert(1.0, content)
        
        # Info bar
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill='x', pady=(5, 0))
        
        lines = len(content.split('\n'))
        chars = len(content)
        info_text = f"Lines: {lines} | Characters: {chars} | File: {title}"
        ttk.Label(info_frame, text=info_text, font=('TkDefaultFont', 8)).pack(side='left')
        
        # Close button
        ttk.Button(info_frame, text="Close", command=self.dialog.destroy).pack(side='right')
        
        # Scroll to bottom
        self.log_text.see(tk.END)
    
    def refresh_log(self, title, original_content):
        """Refresh log content"""
        # In a real implementation, this would re-read the log file
        self.status_bar.config(text="Log refreshed")
    
    def save_log(self):
        """Save log to file"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                content = self.log_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Log saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {e}")
    
    def clear_log(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)
    
    def search_log(self, event=None):
        """Search in log content"""
        search_term = self.search_entry.get().strip()
        if not search_term:
            return
        
        # Clear previous search highlights
        self.log_text.tag_remove('search', 1.0, tk.END)
        
        # Search and highlight
        start_pos = '1.0'
        count = 0
        while True:
            pos = self.log_text.search(search_term, start_pos, tk.END, nocase=True)
            if not pos:
                break
            
            end_pos = f"{pos}+{len(search_term)}c"
            self.log_text.tag_add('search', pos, end_pos)
            start_pos = end_pos
            count += 1
        
        # Configure search highlight
        self.log_text.tag_config('search', background='yellow', foreground='black')
        
        if count > 0:
            # Jump to first match
            first_match = self.log_text.search(search_term, 1.0, tk.END, nocase=True)
            self.log_text.see(first_match)
            messagebox.showinfo("Search Results", f"Found {count} matches")
        else:
            messagebox.showinfo("Search Results", f"No matches found for '{search_term}'")


def main():
    """Main application entry point"""
    # Check if running with appropriate permissions
    if os.name != 'nt':
        # Check if crontab is available
        try:
            subprocess.run(['which', 'crontab'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: crontab not found. Cron functionality may be limited.")
    
    root = tk.Tk()
    
    # Configure ttk style for dark theme
    style = ttk.Style()
    style.theme_use('clam')
    
    # Configure colors for dark theme
    style.configure('TFrame', background='#2b2b2b')
    style.configure('TLabel', background='#2b2b2b', foreground='white')
    style.configure('TButton', background='#404040', foreground='white')
    style.configure('TEntry', background='#404040', foreground='white', fieldbackground='#404040')
    style.configure('TCombobox', background='#404040', foreground='white', fieldbackground='#404040')
    style.configure('TNotebook', background='#2b2b2b', foreground='white')
    style.configure('TNotebook.Tab', background='#404040', foreground='white', padding=[10, 5])
    style.map('TNotebook.Tab', background=[('selected', '#606060')])
    
    app = TerminalManager(root)
    
    # Handle window closing
    def on_closing():
        if messagebox.askokcancel("Quit", "Do you want to quit Terminal Manager?"):
            # Clean up any running processes
            if hasattr(app, 'current_ssh_process') and app.current_ssh_process:
                try:
                    app.current_ssh_process.terminate()
                except:
                    pass
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center the main window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    print("Terminal Manager starting...")
    print("Features:")
    print("• File Editor with terminal editor integration")
    print("• Cron Job Manager with GUI interface")
    print("• SSH Connection Manager")
    print("• Integrated Terminal")
    print("• System Monitor")
    print("\nStarting GUI...")
    
    # Start the application
    root.mainloop()


if __name__ == "__main__":
    main()