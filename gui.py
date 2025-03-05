"""
Weather Sounding Data Tool - GUI Interface

A simple graphical interface for fetching and processing weather sounding data.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import datetime
import subprocess
import pandas as pd
import webbrowser
from tkcalendar import (
    DateEntry,
)  # You might need to install this: pip install tkcalendar

# Set working directory to script location
os.chdir(os.path.dirname(os.path.abspath(__file__)))


class RedirectText:
    """Redirect print statements to the Text widget"""

    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        self.buffer += string
        # We need to schedule this to run in the main thread
        self.text_widget.after(10, self.update_text_widget)

    def update_text_widget(self):
        self.text_widget.configure(state=tk.NORMAL)
        self.text_widget.insert(tk.END, self.buffer)
        self.text_widget.see(tk.END)  # Auto-scroll to the end
        self.text_widget.configure(state=tk.DISABLED)
        self.buffer = ""

    def flush(self):
        pass


class WeatherToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Sounding Data Tool")
        self.root.geometry("800x600")

        # Create a notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self.fetch_tab = ttk.Frame(self.notebook)
        self.process_tab = ttk.Frame(self.notebook)
        self.about_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.fetch_tab, text="Fetch Data")
        self.notebook.add(self.process_tab, text="Process Data")
        self.notebook.add(self.about_tab, text="About")

        # Set up the tabs
        self.setup_fetch_tab()
        self.setup_process_tab()
        self.setup_about_tab()

        # Output console (shared between tabs)
        frame = ttk.LabelFrame(root, text="Output Console")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.console = tk.Text(frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add scrollbar to console
        scrollbar = ttk.Scrollbar(self.console, command=self.console.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console.config(yscrollcommand=scrollbar.set)

        # Redirect stdout to the console
        self.redirect = RedirectText(self.console)
        sys.stdout = self.redirect

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(
            root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_fetch_tab(self):
        # Create a frame for the input fields
        frame = ttk.LabelFrame(self.fetch_tab, text="Fetch Weather Sounding Data")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Year selection
        ttk.Label(frame, text="Year:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 10, current_year + 1))
        self.year_var = tk.StringVar(value=str(current_year))
        year_combo = ttk.Combobox(
            frame, textvariable=self.year_var, values=years, width=10
        )
        year_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Month selection
        ttk.Label(frame, text="Month:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        months = [
            (str(i), datetime.date(2000, i, 1).strftime("%B")) for i in range(1, 13)
        ]
        month_names = [f"{m[0]} - {m[1]}" for m in months]
        self.month_var = tk.StringVar(value="1 - January")
        month_combo = ttk.Combobox(
            frame, textvariable=self.month_var, values=month_names, width=20
        )
        month_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Option to fetch multiple months
        self.multi_month_var = tk.BooleanVar(value=False)
        multi_month_check = ttk.Checkbutton(
            frame,
            text="Fetch multiple months",
            variable=self.multi_month_var,
            command=self.toggle_end_month,
        )
        multi_month_check.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)

        # End month (initially disabled)
        ttk.Label(frame, text="End Month:").grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=5
        )
        self.end_month_var = tk.StringVar(value="12 - December")
        self.end_month_combo = ttk.Combobox(
            frame,
            textvariable=self.end_month_var,
            values=month_names,
            width=20,
            state=tk.DISABLED,
        )
        self.end_month_combo.grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)

        # Station ID
        ttk.Label(frame, text="Station ID:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.station_var = tk.StringVar(
            value="26075"
        )  # Default station (St. Petersburg)
        station_entry = ttk.Entry(frame, textvariable=self.station_var, width=12)
        station_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Add a helper button to find station IDs
        station_help_btn = ttk.Button(
            frame, text="Find Stations", command=self.open_station_list
        )
        station_help_btn.grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        # Button frame
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=20)

        # Add Fetch button
        fetch_btn = ttk.Button(btn_frame, text="Fetch Data", command=self.fetch_data)
        fetch_btn.pack(side=tk.LEFT, padx=5)

        # Add Process Immediately checkbox
        self.process_after_var = tk.BooleanVar(value=True)
        process_check = ttk.Checkbutton(
            btn_frame, text="Process after fetching", variable=self.process_after_var
        )
        process_check.pack(side=tk.LEFT, padx=20)

        # Information text
        info_text = (
            "This tool downloads weather sounding data from the University of Wyoming database.\n"
            "The data will be saved locally to avoid connection issues."
        )
        info_label = ttk.Label(frame, text=info_text, wraplength=600, justify=tk.LEFT)
        info_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=5, pady=10)

    def setup_process_tab(self):
        # Create a frame for the input fields
        frame = ttk.LabelFrame(self.process_tab, text="Process Weather Sounding Data")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Year selection (same as fetch tab)
        ttk.Label(frame, text="Year:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        current_year = datetime.datetime.now().year
        years = list(range(current_year - 10, current_year + 1))
        self.process_year_var = tk.StringVar(value=str(current_year))
        year_combo = ttk.Combobox(
            frame, textvariable=self.process_year_var, values=years, width=10
        )
        year_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Month selection
        ttk.Label(frame, text="Month:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        months = [
            (str(i), datetime.date(2000, i, 1).strftime("%B")) for i in range(1, 13)
        ]
        month_names = [f"{m[0]} - {m[1]}" for m in months]
        self.process_month_var = tk.StringVar(value="1 - January")
        month_combo = ttk.Combobox(
            frame, textvariable=self.process_month_var, values=month_names, width=20
        )
        month_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Option to process multiple months
        self.process_multi_month_var = tk.BooleanVar(value=False)
        multi_month_check = ttk.Checkbutton(
            frame,
            text="Process multiple months",
            variable=self.process_multi_month_var,
            command=self.toggle_process_end_month,
        )
        multi_month_check.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)

        # End month (initially disabled)
        ttk.Label(frame, text="End Month:").grid(
            row=2, column=1, sticky=tk.W, padx=5, pady=5
        )
        self.process_end_month_var = tk.StringVar(value="12 - December")
        self.process_end_month_combo = ttk.Combobox(
            frame,
            textvariable=self.process_end_month_var,
            values=month_names,
            width=20,
            state=tk.DISABLED,
        )
        self.process_end_month_combo.grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)

        # Station ID
        ttk.Label(frame, text="Station ID:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.process_station_var = tk.StringVar(
            value="26075"
        )  # Default station (St. Petersburg)
        station_entry = ttk.Entry(
            frame, textvariable=self.process_station_var, width=12
        )
        station_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Data source option
        ttk.Label(frame, text="Data Source:").grid(
            row=4, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.data_source_var = tk.StringVar(value="local")
        source_local = ttk.Radiobutton(
            frame, text="Use local files", variable=self.data_source_var, value="local"
        )
        source_local.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        source_fetch = ttk.Radiobutton(
            frame, text="Fetch from web", variable=self.data_source_var, value="fetch"
        )
        source_fetch.grid(row=4, column=2, sticky=tk.W, padx=5, pady=5)

        # Button frame
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=20)

        # Add Process button
        process_btn = ttk.Button(
            btn_frame, text="Process Data", command=self.process_data
        )
        process_btn.pack(side=tk.LEFT, padx=5)

        # Add Open Results button
        open_results_btn = ttk.Button(
            btn_frame, text="Open Results Folder", command=self.open_results_folder
        )
        open_results_btn.pack(side=tk.LEFT, padx=5)

        # Add Open Excel button
        open_excel_btn = ttk.Button(
            btn_frame, text="Open DATA.xlsx", command=self.open_excel_file
        )
        open_excel_btn.pack(side=tk.LEFT, padx=5)

        # Information text
        info_text = (
            "This will process previously fetched data to extract temperature inversions.\n"
            "Results will be saved both as individual files and a combined DATA.xlsx file."
        )
        info_label = ttk.Label(frame, text=info_text, wraplength=600, justify=tk.LEFT)
        info_label.grid(row=6, column=0, columnspan=3, sticky=tk.W, padx=5, pady=10)

    def setup_about_tab(self):
        frame = ttk.Frame(self.about_tab)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title = ttk.Label(
            frame, text="Weather Sounding Data Tool", font=("TkDefaultFont", 16, "bold")
        )
        title.pack(pady=10)

        # Description
        description = (
            "This tool helps you fetch and process weather sounding data from the University of Wyoming database.\n\n"
            "It extracts temperature inversions below 1000m and creates Excel files with detailed analysis.\n\n"
            "The tool is designed to work with saved HTML files to avoid connection issues."
        )
        desc_label = ttk.Label(
            frame, text=description, wraplength=700, justify=tk.CENTER
        )
        desc_label.pack(pady=10)

        # GitHub link
        github_frame = ttk.Frame(frame)
        github_frame.pack(pady=10)
        ttk.Label(github_frame, text="GitHub Repository: ").pack(side=tk.LEFT)
        github_link = ttk.Label(
            github_frame,
            text="https://github.com/yourusername/weather-sounding-tool",
            foreground="blue",
            cursor="hand2",
        )
        github_link.pack(side=tk.LEFT)
        github_link.bind(
            "<Button-1>",
            lambda e: webbrowser.open_new(
                "https://github.com/yourusername/weather-sounding-tool"
            ),
        )

        # Usage tips
        tips_text = (
            "Tips:\n\n"
            "1. Fetch data once and then process it multiple times\n"
            "2. Station 26075 is St. Petersburg (Russia)\n"
            "3. Results are saved in 'soundings_YEAR_STATION' folder\n"
            "4. Combined analysis is in DATA.xlsx"
        )
        tips_frame = ttk.LabelFrame(frame, text="Usage Tips")
        tips_frame.pack(pady=20, fill=tk.X)
        tips_label = ttk.Label(
            tips_frame, text=tips_text, wraplength=700, justify=tk.LEFT
        )
        tips_label.pack(padx=10, pady=10)

    def toggle_end_month(self):
        """Enable or disable the end month combobox based on the multi-month checkbox"""
        if self.multi_month_var.get():
            self.end_month_combo.config(state=tk.NORMAL)
        else:
            self.end_month_combo.config(state=tk.DISABLED)

    def toggle_process_end_month(self):
        """Enable or disable the end month combobox in the process tab"""
        if self.process_multi_month_var.get():
            self.process_end_month_combo.config(state=tk.NORMAL)
        else:
            self.process_end_month_combo.config(state=tk.DISABLED)

    def open_station_list(self):
        """Open the Wyoming website to find station IDs"""
        webbrowser.open_new("http://weather.uwyo.edu/upperair/sounding.html")
        self.status_var.set("Opened station list in browser")

    def extract_month_number(self, month_string):
        """Extract the month number from strings like '1 - January'"""
        return int(month_string.split(" - ")[0])

    def fetch_data(self):
        """Fetch data using the weather_tool.py script"""
        # Get values from GUI
        year = self.year_var.get()
        start_month = self.extract_month_number(self.month_var.get())
        station = self.station_var.get()

        # Build command
        cmd = [
            "python",
            "weather_tool.py",
            "--fetch",
            "--year",
            year,
            "--month",
            str(start_month),
            "--station",
            station,
        ]

        # Add end month if needed
        if self.multi_month_var.get():
            end_month = self.extract_month_number(self.end_month_var.get())
            cmd.extend(["--end-month", str(end_month)])

        self.status_var.set(f"Fetching data for {year}, month(s) {start_month}...")
        self.console.configure(state=tk.NORMAL)
        self.console.insert(
            tk.END, f"\n{'-'*80}\nStarting data fetch: {' '.join(cmd)}\n{'-'*80}\n"
        )
        self.console.configure(state=tk.DISABLED)

        # Run in a thread to keep GUI responsive
        def run_command():
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )

                # Read output line by line
                for line in iter(process.stdout.readline, ""):
                    print(line, end="")  # This will go to our redirected stdout

                process.stdout.close()
                return_code = process.wait()

                if return_code == 0:
                    self.status_var.set("Data fetching completed successfully")
                    # Process if checkbox is checked
                    if self.process_after_var.get():
                        self.root.after(
                            500, self.process_data
                        )  # Schedule processing after a short delay
                else:
                    self.status_var.set(
                        f"Data fetching failed with return code {return_code}"
                    )
            except Exception as e:
                print(f"Error running command: {e}")
                self.status_var.set(f"Error: {e}")

        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()

    def process_data(self):
        """Process data using the weather_tool.py script"""
        # Get values from GUI
        year = self.process_year_var.get()
        start_month = self.extract_month_number(self.process_month_var.get())
        station = self.process_station_var.get()

        # Build command
        cmd = [
            "python",
            "weather_tool.py",
            "--process",
            "--year",
            year,
            "--month",
            str(start_month),
            "--station",
            station,
        ]

        # Add end month if needed
        if self.process_multi_month_var.get():
            end_month = self.extract_month_number(self.process_end_month_var.get())
            cmd.extend(["--end-month", str(end_month)])

        # Use local files if selected
        if self.data_source_var.get() == "local":
            cmd.append("--use-local")

        self.status_var.set(f"Processing data for {year}, month(s) {start_month}...")
        self.console.configure(state=tk.NORMAL)
        self.console.insert(
            tk.END, f"\n{'-'*80}\nStarting data processing: {' '.join(cmd)}\n{'-'*80}\n"
        )
        self.console.configure(state=tk.DISABLED)

        # Run in a thread to keep GUI responsive
        def run_command():
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )

                # Read output line by line
                for line in iter(process.stdout.readline, ""):
                    print(line, end="")  # This will go to our redirected stdout

                process.stdout.close()
                return_code = process.wait()

                if return_code == 0:
                    self.status_var.set("Data processing completed successfully")
                    self.root.after(
                        500,
                        lambda: messagebox.showinfo(
                            "Processing Complete",
                            "Data processing completed successfully!\n\n"
                            f"Individual files saved in: soundings_{year}_{station}/\n"
                            "Combined analysis saved in: DATA.xlsx",
                        ),
                    )
                else:
                    self.status_var.set(
                        f"Data processing failed with return code {return_code}"
                    )
            except Exception as e:
                print(f"Error running command: {e}")
                self.status_var.set(f"Error: {e}")

        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()

    def open_results_folder(self):
        """Open the output folder containing individual Excel files"""
        year = self.process_year_var.get()
        station = self.process_station_var.get()
        folder_path = f"soundings_{year}_{station}"

        # Check if folder exists
        if not os.path.exists(folder_path):
            messagebox.showinfo(
                "Folder Not Found",
                f"The folder {folder_path} doesn't exist yet.\n\n"
                "Process some data first to create it.",
            )
            return

        # Open folder
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def open_excel_file(self):
        """Open the DATA.xlsx file"""
        file_path = "DATA.xlsx"

        # Check if file exists
        if not os.path.exists(file_path):
            messagebox.showinfo(
                "File Not Found",
                "DATA.xlsx doesn't exist yet.\n\n"
                "Process some data first to create it.",
            )
            return

        # Open Excel file
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open Excel file: {e}")


def main():
    root = tk.Tk()
    app = WeatherToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
