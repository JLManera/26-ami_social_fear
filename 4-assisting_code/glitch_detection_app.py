import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading


class GlitchDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Glitch Detector")
        self.root.geometry("1200x800")
        
        # Video data
        self.video_path = None
        self.frame_diffs = None
        self.frame_indices = None
        self.total_frames = 0
        self.fps = 30
        self.frame_width = 0
        self.frame_height = 0
        self.glitch_indices = []
        self.current_preview_index = 0
        
        # Cache for preview frames
        self.frame_cache = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === TOP: File Selection ===
        file_frame = ttk.LabelFrame(main_frame, text="Video File", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.browse_btn = ttk.Button(file_frame, text="Browse...", command=self._browse_file)
        self.browse_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.load_btn = ttk.Button(file_frame, text="Analyze Video", command=self._start_analysis, state=tk.DISABLED)
        self.load_btn.pack(side=tk.RIGHT)
        
        # === Progress bar ===
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack()
        
        # === MIDDLE: Controls and Results ===
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Left side: Slider and stats
        left_frame = ttk.Frame(middle_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Threshold controls
        threshold_frame = ttk.LabelFrame(left_frame, text="Threshold Settings", padding="10")
        threshold_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(threshold_frame, text="MAD Multiplier:").pack(anchor=tk.W)
        
        slider_frame = ttk.Frame(threshold_frame)
        slider_frame.pack(fill=tk.X, pady=5)
        
        self.mad_multiplier = tk.DoubleVar(value=6.0)
        self.mad_slider = ttk.Scale(
            slider_frame, 
            from_=1.0, 
            to=100.0, 
            variable=self.mad_multiplier,
            orient=tk.HORIZONTAL,
            command=self._on_slider_change
        )
        self.mad_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.mad_entry = ttk.Entry(slider_frame, width=8)
        self.mad_entry.insert(0, "6.0")
        self.mad_entry.pack(side=tk.RIGHT, padx=(5, 0))
        self.mad_entry.bind('<Return>', self._on_entry_change)
        self.mad_entry.bind('<FocusOut>', self._on_entry_change)
        
        self.mad_label = ttk.Label(slider_frame, text="6.0", width=5)
        self.mad_label.pack_forget()  # Hide the old label, using entry instead
        
        # Statistics display
        stats_frame = ttk.LabelFrame(left_frame, text="Statistics", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_text = tk.Text(stats_frame, height=6, width=40, state=tk.DISABLED)
        self.stats_text.pack(fill=tk.X)
        
        # Glitch frames list
        list_frame = ttk.LabelFrame(left_frame, text="Detected Glitch Frames", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.glitch_listbox = tk.Listbox(list_container, selectmode=tk.SINGLE)
        self.glitch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.glitch_listbox.bind('<<ListboxSelect>>', self._on_listbox_select)
        
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.glitch_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.glitch_listbox.config(yscrollcommand=scrollbar.set)
        
        # Right side: Frame preview
        right_frame = ttk.Frame(middle_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        preview_frame = ttk.LabelFrame(right_frame, text="Frame Preview", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Navigation buttons
        nav_frame = ttk.Frame(preview_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.prev_btn = ttk.Button(nav_frame, text="← Previous", command=self._prev_frame, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT)
        
        self.frame_info_label = ttk.Label(nav_frame, text="No frames to display")
        self.frame_info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.next_btn = ttk.Button(nav_frame, text="Next →", command=self._next_frame, state=tk.DISABLED)
        self.next_btn.pack(side=tk.RIGHT)
        
        # Canvas for frame display (3 frames: before, glitch, after)
        canvas_container = ttk.Frame(preview_frame)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Three preview panels
        self.preview_labels = []
        self.preview_titles = ["Previous Frame", "Glitch Frame", "Next Frame"]
        
        for i, title in enumerate(self.preview_titles):
            panel = ttk.Frame(canvas_container)
            panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
            
            ttk.Label(panel, text=title, font=('Arial', 10, 'bold')).pack()
            
            canvas = tk.Canvas(panel, width=240, height=180, bg='black')
            canvas.pack(fill=tk.BOTH, expand=True)
            self.preview_labels.append(canvas)
        
        # === BOTTOM: Export ===
        export_frame = ttk.LabelFrame(main_frame, text="Export", padding="10")
        export_frame.pack(fill=tk.X)
        
        export_inner = ttk.Frame(export_frame)
        export_inner.pack(fill=tk.X)
        
        ttk.Label(export_inner, text="Output filename suffix:").pack(side=tk.LEFT)
        
        self.suffix_var = tk.StringVar(value="_cleaned")
        self.suffix_entry = ttk.Entry(export_inner, textvariable=self.suffix_var, width=20)
        self.suffix_entry.pack(side=tk.LEFT, padx=(5, 20))
        
        self.export_btn = ttk.Button(
            export_inner, 
            text="Export Video (Replace Glitches with Black)", 
            command=self._start_export,
            state=tk.DISABLED
        )
        self.export_btn.pack(side=tk.RIGHT)
    
    def _browse_file(self):
        filetypes = [
            ("Video files", "*.mkv *.mp4 *.avi *.mov *.wmv *.flv *.webm"),
            ("All files", "*.*")
        ]
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.video_path = path
            self.file_label.config(text=os.path.basename(path))
            self.load_btn.config(state=tk.NORMAL)
            self.frame_cache.clear()
    
    def _start_analysis(self):
        if not self.video_path:
            return
        
        # Disable controls during analysis
        self.load_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        
        # Run analysis in background thread
        thread = threading.Thread(target=self._analyze_video)
        thread.daemon = True
        thread.start()
    
    def _analyze_video(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("Error", f"Could not open video: {self.video_path}"))
                return
            
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS) or 30
            self.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # First pass: compute diffs between consecutive frames
            consecutive_diffs = []
            frame_indices = []
            prev_gray = None
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    score = float(diff.mean())
                    consecutive_diffs.append(score)
                    frame_indices.append(frame_idx)
                
                prev_gray = gray
                frame_idx += 1
                
                # Update progress
                if frame_idx % 50 == 0:
                    progress = (frame_idx / self.total_frames) * 50  # First pass is 50%
                    self.root.after(0, lambda p=progress, f=frame_idx: self._update_progress(p, f"Pass 1/2: Analyzing frame {f}/{self.total_frames}"))
            
            cap.release()
            
            # Store consecutive diffs for initial threshold calculation
            self.consecutive_diffs = np.array(consecutive_diffs)
            self.frame_indices = frame_indices
            
            # Second pass: compute diffs against last known good frame
            # This handles consecutive glitches properly
            self.root.after(0, lambda: self._update_progress(50, "Pass 2/2: Computing reference-based diffs..."))
            
            cap = cv2.VideoCapture(self.video_path)
            
            # Calculate initial threshold from consecutive diffs
            median = np.median(self.consecutive_diffs)
            mad = np.median(np.abs(self.consecutive_diffs - median))
            if mad == 0:
                initial_threshold = median + 6 * self.consecutive_diffs.std()
            else:
                initial_threshold = median + 6 * mad
            
            reference_diffs = []
            reference_gray = None
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if reference_gray is not None:
                    diff = cv2.absdiff(gray, reference_gray)
                    score = float(diff.mean())
                    reference_diffs.append(score)
                    
                    # Only update reference if this frame is likely NOT a glitch
                    # Use a conservative threshold for this decision
                    if score <= initial_threshold:
                        reference_gray = gray
                else:
                    reference_diffs.append(0)
                    reference_gray = gray
                
                frame_idx += 1
                
                if frame_idx % 50 == 0:
                    progress = 50 + (frame_idx / self.total_frames) * 50
                    self.root.after(0, lambda p=progress, f=frame_idx: self._update_progress(p, f"Pass 2/2: Frame {f}/{self.total_frames}"))
            
            cap.release()
            
            # Use reference-based diffs for glitch detection
            self.frame_diffs = np.array(reference_diffs[1:])  # Skip first frame (no diff)
            self.frame_indices = list(range(1, len(reference_diffs)))
            
            # Finish up on main thread
            self.root.after(0, self._analysis_complete)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self._reset_controls)
    
    def _update_progress(self, value, text):
        self.progress_var.set(value)
        self.progress_label.config(text=text)
    
    def _analysis_complete(self):
        self.progress_var.set(100)
        self.progress_label.config(text="Analysis complete!")
        
        # Re-enable controls
        self.load_btn.config(state=tk.NORMAL)
        self.browse_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        self.prev_btn.config(state=tk.NORMAL)
        self.next_btn.config(state=tk.NORMAL)
        
        # Update glitch list
        self._update_glitch_list()
    
    def _reset_controls(self):
        self.load_btn.config(state=tk.NORMAL)
        self.browse_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_label.config(text="")
    
    def _on_slider_change(self, value):
        val = float(value)
        self.mad_entry.delete(0, tk.END)
        self.mad_entry.insert(0, f"{val:.1f}")
        if self.frame_diffs is not None:
            self._update_glitch_list()
    
    def _on_entry_change(self, event=None):
        try:
            val = float(self.mad_entry.get())
            if val < 0:
                val = 0
            self.mad_multiplier.set(min(val, 100.0))  # Slider maxes at 100
            if self.frame_diffs is not None:
                # Use the actual entered value (can exceed slider max)
                self._update_glitch_list(override_multiplier=val)
        except ValueError:
            # Reset to current slider value if invalid input
            self.mad_entry.delete(0, tk.END)
            self.mad_entry.insert(0, f"{self.mad_multiplier.get():.1f}")
    
    def _update_glitch_list(self, override_multiplier=None):
        if self.frame_diffs is None:
            return
        
        multiplier = override_multiplier if override_multiplier is not None else self.mad_multiplier.get()
        
        # Calculate threshold
        median = np.median(self.frame_diffs)
        mad = np.median(np.abs(self.frame_diffs - median))
        
        if mad == 0:
            std = self.frame_diffs.std()
            threshold = median + multiplier * std
            threshold_type = "STD"
        else:
            threshold = median + multiplier * mad
            threshold_type = "MAD"
        
        # Find glitches
        self.glitch_indices = [idx for idx, score in zip(self.frame_indices, self.frame_diffs) if score > threshold]
        
        # Update listbox
        self.glitch_listbox.delete(0, tk.END)
        for idx in self.glitch_indices:
            score = self.frame_diffs[self.frame_indices.index(idx)]
            time_sec = idx / self.fps
            self.glitch_listbox.insert(tk.END, f"Frame {idx} (t={time_sec:.2f}s, score={score:.2f})")
        
        # Update statistics
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        stats = f"""Total frames: {self.total_frames}
FPS: {self.fps:.2f}
Duration: {self.total_frames/self.fps:.2f}s
Median diff: {median:.4f}
{threshold_type}: {mad if threshold_type == 'MAD' else std:.4f}
Threshold: {threshold:.4f}
Glitches found: {len(self.glitch_indices)}"""
        self.stats_text.insert(1.0, stats)
        self.stats_text.config(state=tk.DISABLED)
        
        # Update preview
        self.current_preview_index = 0
        self._update_preview()
    
    def _on_listbox_select(self, event):
        selection = self.glitch_listbox.curselection()
        if selection:
            self.current_preview_index = selection[0]
            self._update_preview()
    
    def _prev_frame(self):
        if self.glitch_indices and self.current_preview_index > 0:
            self.current_preview_index -= 1
            self.glitch_listbox.selection_clear(0, tk.END)
            self.glitch_listbox.selection_set(self.current_preview_index)
            self.glitch_listbox.see(self.current_preview_index)
            self._update_preview()
    
    def _next_frame(self):
        if self.glitch_indices and self.current_preview_index < len(self.glitch_indices) - 1:
            self.current_preview_index += 1
            self.glitch_listbox.selection_clear(0, tk.END)
            self.glitch_listbox.selection_set(self.current_preview_index)
            self.glitch_listbox.see(self.current_preview_index)
            self._update_preview()
    
    def _get_frame(self, frame_idx):
        """Get a frame from the video, using cache if available."""
        if frame_idx < 0 or frame_idx >= self.total_frames:
            return None
        
        if frame_idx in self.frame_cache:
            return self.frame_cache[frame_idx]
        
        cap = cv2.VideoCapture(self.video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            # Limit cache size
            if len(self.frame_cache) > 100:
                # Remove oldest entries
                keys = list(self.frame_cache.keys())[:50]
                for k in keys:
                    del self.frame_cache[k]
            
            self.frame_cache[frame_idx] = frame
            return frame
        return None
    
    def _update_preview(self):
        if not self.glitch_indices:
            self.frame_info_label.config(text="No glitch frames detected")
            for canvas in self.preview_labels:
                canvas.delete("all")
            return
        
        glitch_frame_idx = self.glitch_indices[self.current_preview_index]
        self.frame_info_label.config(
            text=f"Glitch {self.current_preview_index + 1} of {len(self.glitch_indices)} | Frame {glitch_frame_idx}"
        )
        
        # Get the three frames to display
        frame_indices_to_show = [
            glitch_frame_idx - 1,  # Previous
            glitch_frame_idx,       # Glitch
            glitch_frame_idx + 1    # Next
        ]
        
        for i, (canvas, fidx) in enumerate(zip(self.preview_labels, frame_indices_to_show)):
            canvas.delete("all")
            
            frame = self._get_frame(fidx)
            if frame is not None:
                # Resize for display
                canvas_width = canvas.winfo_width() or 240
                canvas_height = canvas.winfo_height() or 180
                
                # Calculate aspect-correct resize
                h, w = frame.shape[:2]
                scale = min(canvas_width / w, canvas_height / h)
                new_w, new_h = int(w * scale), int(h * scale)
                
                resized = cv2.resize(frame, (new_w, new_h))
                # Convert BGR to RGB
                rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                photo = ImageTk.PhotoImage(img)
                
                # Store reference to prevent garbage collection
                canvas.image = photo
                canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
            else:
                canvas.create_text(
                    canvas.winfo_width() // 2 or 120, 
                    canvas.winfo_height() // 2 or 90, 
                    text="N/A", 
                    fill="white"
                )
    
    def _start_export(self):
        if not self.video_path or not self.glitch_indices:
            messagebox.showinfo("Info", "No glitch frames to replace.")
            return
        
        # Generate output path
        base, ext = os.path.splitext(self.video_path)
        suffix = self.suffix_var.get()
        output_path = f"{base}{suffix}{ext}"
        
        # Confirm
        if os.path.exists(output_path):
            if not messagebox.askyesno("Confirm", f"Output file exists:\n{output_path}\n\nOverwrite?"):
                return
        
        # Disable controls
        self.export_btn.config(state=tk.DISABLED)
        self.load_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        
        # Run export in background
        thread = threading.Thread(target=self._export_video, args=(output_path,))
        thread.daemon = True
        thread.start()
    
    def _export_video(self, output_path):
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.root.after(0, lambda: messagebox.showerror("Error", "Could not open video for export"))
                return
            
            # Get video properties
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use mp4v codec
            
            # For MKV, try to use the same codec or fallback
            ext = os.path.splitext(output_path)[1].lower()
            if ext == '.mkv':
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
            elif ext == '.avi':
                fourcc = cv2.VideoWriter_fourcc(*'XVID')
            
            out = cv2.VideoWriter(
                output_path, 
                fourcc, 
                self.fps, 
                (self.frame_width, self.frame_height)
            )
            
            if not out.isOpened():
                self.root.after(0, lambda: messagebox.showerror("Error", "Could not create output video"))
                cap.release()
                return
            
            glitch_set = set(self.glitch_indices)
            black_frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
            
            frame_idx = 0
            replaced_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_idx in glitch_set:
                    out.write(black_frame)
                    replaced_count += 1
                else:
                    out.write(frame)
                
                frame_idx += 1
                
                if frame_idx % 100 == 0:
                    progress = (frame_idx / self.total_frames) * 100
                    self.root.after(0, lambda p=progress, f=frame_idx: self._update_progress(p, f"Exporting frame {f}/{self.total_frames}"))
            
            cap.release()
            out.release()
            
            self.root.after(0, lambda: self._export_complete(output_path, replaced_count))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Export failed: {str(e)}"))
            self.root.after(0, self._reset_controls)
    
    def _export_complete(self, output_path, replaced_count):
        self.progress_var.set(100)
        self.progress_label.config(text="Export complete!")
        
        # Re-enable controls
        self.export_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        self.browse_btn.config(state=tk.NORMAL)
        
        messagebox.showinfo(
            "Export Complete", 
            f"Video exported successfully!\n\n"
            f"Output: {output_path}\n"
            f"Frames replaced: {replaced_count}"
        )


def main():
    root = tk.Tk()
    app = GlitchDetectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
