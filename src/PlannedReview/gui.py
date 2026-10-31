from pathlib import Path
import queue
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from tkinterdnd2 import DND_FILES, TkinterDnD

from plannedreview import PlannedReview


class PlannedReviewApp:
    def __init__(self, root: TkinterDnD.Tk) -> None:
        self.root = root
        self.root.title("PlannedReview")
        self.root.geometry("720x640")
        self.root.minsize(540, 420)

        self.pdf_path: Path | None = None
        self.reviewed_pdf: Path | None = None
        self.events: queue.Queue[tuple[str, str | Path]] = queue.Queue()

        container = ttk.Frame(root, padding=24)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text="Review a construction plan",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            container,
            text="Drop one PDF below, or browse to select a file.",
        ).pack(anchor=tk.W, pady=(4, 16))

        self.drop_area = ttk.Label(
            container,
            text="Drop PDF here",
            anchor=tk.CENTER,
            relief=tk.GROOVE,
            padding=20,
        )
        self.drop_area.pack(fill=tk.X)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind("<<Drop>>", self._on_drop)

        self.file_label = ttk.Label(container, text="No PDF selected", wraplength=500)
        self.file_label.pack(anchor=tk.W, pady=(10, 8))

        actions = ttk.Frame(container)
        actions.pack(fill=tk.X)
        self.browse_button = ttk.Button(actions, text="Choose PDF...", command=self._browse)
        self.browse_button.pack(side=tk.LEFT)
        self.review_button = ttk.Button(
            actions,
            text="Start review",
            command=self._start_review,
            state=tk.DISABLED,
        )
        self.review_button.pack(side=tk.LEFT, padx=(8, 0))
        self.save_button = ttk.Button(
            actions,
            text="Save reviewed PDF as...",
            command=self._save_reviewed_pdf,
            state=tk.DISABLED,
        )
        self.save_button.pack(side=tk.RIGHT)

        self.progress = ttk.Progressbar(container, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(16, 8))
        self.progress.stop()
        self.progress.pack_forget()
        self.status_label = ttk.Label(container, text="Ready")
        self.status_label.pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(container, text="Review output").pack(anchor=tk.W)
        self.output_area = ScrolledText(
            container,
            height=14,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 9),
        )
        self.output_area.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.root.after(200, self._check_results)

    def _browse(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select a construction plan PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if selected:
            self._set_pdf(Path(selected))

    def _on_drop(self, event: tk.Event) -> None:
        dropped_paths = self.root.tk.splitlist(event.data)
        if len(dropped_paths) != 1:
            messagebox.showerror("Select one PDF", "Please drop one PDF file at a time.")
            return
        self._set_pdf(Path(dropped_paths[0]))

    def _set_pdf(self, path: Path) -> None:
        path = path.expanduser()
        if path.suffix.lower() != ".pdf":
            messagebox.showerror("Invalid file", "Please select a PDF file.")
            return
        if not path.is_file():
            messagebox.showerror("File not found", f"Could not find:\n{path}")
            return

        self.pdf_path = path.resolve()
        self.reviewed_pdf = None
        self.file_label.configure(text=str(self.pdf_path))
        self.review_button.configure(state=tk.NORMAL)
        self.save_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="Ready to review")

    def _start_review(self) -> None:
        if self.pdf_path is None:
            return

        pdf_path = self.pdf_path
        self._set_busy(True)
        self.status_label.configure(text="Reviewing PDF. This may take several minutes...")
        self._clear_output()
        self._append_output(f"Starting review for {pdf_path}\n\n")
        threading.Thread(
            target=self._run_review,
            args=(pdf_path,),
            daemon=True,
        ).start()

    def _run_review(self, pdf_path: Path) -> None:
        try:
            result = PlannedReview(
                str(pdf_path),
                "None",
                output_callback=self._queue_output,
            )
            if result is None:
                raise RuntimeError("The review did not produce a reviewed PDF.")
            self.events.put(("success", result))
        except Exception as error:
            self.events.put(("error", str(error)))

    def _check_results(self) -> None:
        while True:
            try:
                event_type, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event_type == "output":
                self._append_output(str(payload))
            elif event_type == "success":
                self._set_busy(False)
                self.reviewed_pdf = Path(payload)
                self.save_button.configure(state=tk.NORMAL)
                self.status_label.configure(text=f"Review complete: {self.reviewed_pdf}")
                messagebox.showinfo(
                    "Review complete",
                    "The reviewed PDF is ready. Use “Save reviewed PDF as...” to choose where to save a copy.",
                )
            elif event_type == "error":
                self._set_busy(False)
                self.status_label.configure(text="Review failed")
                self._append_output(f"\nReview failed: {payload}\n")
                messagebox.showerror("Review failed", str(payload))

        self.root.after(200, self._check_results)

    def _queue_output(self, text: str) -> None:
        self.events.put(("output", text))

    def _append_output(self, text: str) -> None:
        self.output_area.configure(state=tk.NORMAL)
        self.output_area.insert(tk.END, text)
        self.output_area.see(tk.END)
        self.output_area.configure(state=tk.DISABLED)

    def _clear_output(self) -> None:
        self.output_area.configure(state=tk.NORMAL)
        self.output_area.delete("1.0", tk.END)
        self.output_area.configure(state=tk.DISABLED)

    def _set_busy(self, busy: bool) -> None:
        self.browse_button.configure(state=tk.DISABLED if busy else tk.NORMAL)
        self.review_button.configure(
            state=tk.DISABLED if busy or self.pdf_path is None else tk.NORMAL
        )
        if busy:
            self.progress.pack(fill=tk.X, pady=(16, 8))
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def _save_reviewed_pdf(self) -> None:
        if self.reviewed_pdf is None:
            return

        destination = filedialog.asksaveasfilename(
            title="Save reviewed PDF",
            initialdir=self.reviewed_pdf.parent,
            initialfile=self.reviewed_pdf.name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not destination:
            return

        destination_path = Path(destination)
        try:
            if destination_path.resolve() != self.reviewed_pdf.resolve():
                shutil.copy2(self.reviewed_pdf, destination_path)
            self.status_label.configure(text=f"Saved reviewed PDF: {destination_path}")
            messagebox.showinfo("PDF saved", f"Reviewed PDF saved to:\n{destination_path}")
        except OSError as error:
            messagebox.showerror("Could not save PDF", str(error))


def main() -> None:
    root = TkinterDnD.Tk()
    PlannedReviewApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
