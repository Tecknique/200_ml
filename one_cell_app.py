# path: one_cell_app.py

"""
Portable ONE-CELL APP (Jupyter/Voilà)
- Starts in the current working directory (repo root by default)
- No hard-coded paths
- Analyzer can sync to Manager's working directory automatically or via a button
- Case-insensitive image discovery; supports .tif/.tiff/.png/.jpg/.jpeg/.bmp
"""

# --- interactive matplotlib backend (graceful fallback) ---
# If you hit startup errors, temporarily comment out the ipympl lines below.
try:
    import matplotlib
    import ipympl  # noqa: F401
    matplotlib.use("module://ipympl.backend_nbagg")
except Exception:
    # Fallback: let Jupyter decide a usable backend without crashing.
    import matplotlib  # type: ignore

# --- imports ---
import os
import glob
from itertools import chain
from typing import Callable, List

import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import ipywidgets as widgets
from ipyfilechooser import FileChooser
from IPython.display import display, clear_output
from datetime import datetime

# =========================
# ImageFolderManager
# =========================
class ImageFolderManager:
    """Manages working directory and image-folder selection.

    Notes
    -----
    - All choosers start at `os.getcwd()` by default.
    - When the working directory changes, registered listeners are notified.
    """

    _last_root = None  # prevent duplicate UIs

    def __init__(self):
        self.selected_folders: List[str] = []
        self.img_list: List[np.ndarray] = []
        self.img_pos: List[np.ndarray] = []
        self.img_neg: List[np.ndarray] = []
        self.file_names: List[str] = []
        self.file_names_pos: List[str] = []
        self.file_names_neg: List[str] = []
        self.cwd = os.getcwd()

        self._cwd_listeners: List[Callable[[str], None]] = []

        self.path_label = widgets.Label(value=f"Current working directory:\n{self.cwd}")

        self.chooser = self._chooser('<b>Select your image database folder</b>', only_dirs=True)
        self.confirm_button = widgets.Button(description="Set as Working Directory", button_style='success')
        self.confirm_button.on_click(self.set_working_directory)

        self.chooser_container = widgets.VBox([self._chooser('<b>Select a folder containing images</b>', only_dirs=True)])
        self.add_button = widgets.Button(description=" Add Folder to List", button_style='info')
        self.done_button = widgets.Button(description="Done Loading Images", button_style='success')
        self.folder_list_label = widgets.Label(value="Selected Folders:")
        self.folder_list_box = widgets.VBox([])
        self.output = widgets.Output()

        self.add_button.on_click(self.on_add_clicked)
        self.done_button.on_click(self.on_done_clicked)
        self._root = None

    # ----- events -----
    def add_cwd_listener(self, fn: Callable[[str], None]) -> None:
        self._cwd_listeners.append(fn)

    # ----- helpers -----
    def _chooser(self, title: str, only_dirs: bool = False) -> FileChooser:
        c = FileChooser(self.cwd)
        c.title = title
        c.show_only_dirs = only_dirs
        c.use_dir_icons = False
        return c

    # ----- UI callbacks -----
    def set_working_directory(self, _):
        # Keep all choosers & widgets aligned with the selected directory.
        if self.chooser.selected_path:
            os.chdir(self.chooser.selected_path)
            self.cwd = self.chooser.selected_path
            self.path_label.value = f"Current working directory:\n{self.cwd}"

            # Refresh the secondary chooser so it starts in the new cwd immediately
            self.chooser_container.children = [self._chooser('<b>Select a folder containing images</b>', only_dirs=True)]
            # Notify listeners
            for fn in self._cwd_listeners:
                try:
                    fn(self.cwd)
                except Exception:
                    pass
        else:
            self.path_label.value = "No folder selected."

    def on_add_clicked(self, _):
        folder = getattr(self.chooser_container.children[0], 'selected_path', None)
        if folder and folder not in self.selected_folders:
            self.selected_folders.append(folder)
            self.folder_list_box.children = [widgets.Label(f) for f in self.selected_folders]
        # Recreate the chooser so it stays rooted at current self.cwd
        self.chooser_container.children = [self._chooser('<b>Select a folder containing images</b>', only_dirs=True)]

    def _iter_image_paths(self, folder: str):
        # Case-insensitive, common formats
        exts = ("*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg", "*.bmp")
        globs = (glob.glob(os.path.join(folder, pat)) for pat in exts)
        for p in chain.from_iterable(globs):
            yield p

    def on_done_clicked(self, _):
        with self.output:
            clear_output()
            if not self.selected_folders:
                print("No folders selected.")
                return
            self.img_list.clear(); self.img_pos.clear(); self.img_neg.clear()
            self.file_names.clear(); self.file_names_pos.clear(); self.file_names_neg.clear()

            for folder in self.selected_folders:
                for img_path in self._iter_image_paths(folder):
                    base = os.path.splitext(os.path.basename(img_path))[0]
                    tag = base.lower()
                    img = cv2.imread(img_path)
                    if img is None:
                        continue
                    if "n1" in tag:
                        self.file_names.append(base); self.img_list.append(img)
                    elif "pos" in tag:
                        self.file_names_pos.append(base); self.img_pos.append(img)
                    elif "neg" in tag:
                        self.file_names_neg.append(base); self.img_neg.append(img)

            print(" Loaded files:")
            print(" Test images (n1):", self.file_names)
            print(" Positive control images (pos):", self.file_names_pos)
            print(" Negative control images (neg):", self.file_names_neg)

    def run(self):
        if ImageFolderManager._last_root is not None:
            try:
                ImageFolderManager._last_root.close()
            except Exception:
                pass
        self._root = widgets.VBox([
            widgets.HTML(value="<h3>Select Working Directory</h3>"),
            self.chooser, self.confirm_button, self.path_label,
            widgets.HTML(value="<hr><h3>Select and Process Image Folders</h3>"),
            self.chooser_container, self.add_button,
            self.folder_list_label, self.folder_list_box,
            self.done_button, self.output
        ])
        ImageFolderManager._last_root = self._root
        display(self._root)

# =========================
# ImageViewerWithROI
# =========================
class ImageViewerWithROI:
    _last_root = None

    def __init__(self, manager: ImageFolderManager):
        self.manager = manager
        self.dropdown = widgets.Dropdown(options=self._get_opts(), description='Choose image:', layout=widgets.Layout(width='60%'))
        self.show_button = widgets.Button(description=" Select ROI", button_style='info')
        self.rotate_button = widgets.Button(description="⟳ Rotate 90°", button_style='primary')
        self.reset_button  = widgets.Button(description=" Reset View",  button_style='warning')
        self.save_K_button = widgets.Button(description="Save as K",    button_style='success')
        self.save_C_button = widgets.Button(description="Save as C",    button_style='success')
        self.export_button = widgets.Button(description="📄 Export to DataFrame", button_style='info')

        self.condition_selector = widgets.Dropdown(options=["N1","N2","N3","N4"], description="Condition:")
        # Keep this list in sync with the loads dicts below
        self.load_selector      = widgets.Dropdown(options=["1e5","1.5e5","2e5","5e5","1e6","5e6","1e7","pos","neg"], description="Load:")
        self.output = widgets.Output()

        self.fig = self.ax = self.rect_selector = None
        self.current_image = self.original_image = None
        self.current_title = ""
        self.saved_regions = {"K": [], "C": []}
        self.date_folder = datetime.today().strftime('%Y-%m-%d')
        self._root = None

        self.show_button.on_click(self.display_with_selector)
        self.rotate_button.on_click(self.rotate_image)
        self.reset_button.on_click(self.reset_display)
        self.save_K_button.on_click(self.save_K)
        self.save_C_button.on_click(self.save_C)
        self.export_button.on_click(self.export_to_dataframe)

    def _get_opts(self):
        return [(name, i) for i, name in enumerate(self.manager.file_names)]

    def display_with_selector(self, _=None):
        with self.output:
            clear_output()
            self.dropdown.options = self._get_opts()
            if not self.dropdown.options:
                print("No images loaded yet. Click 'Done Loading Images' first.")
                return
            if self.dropdown.value is None:
                self.dropdown.value = self.dropdown.options[0][1]
            i = self.dropdown.value
            if i is None or i >= len(self.manager.img_list):
                print("Invalid selection.")
                return
            self.current_image = self.manager.img_list[i]
            self.original_image = self.current_image.copy()
            self.current_title  = self.manager.file_names[i]
            self._draw_with_selector()

    def _draw_with_selector(self):
        if self.fig:
            plt.close(self.fig)
        with self.output:
            clear_output()
            img_rgb = cv2.cvtColor(self.current_image, cv2.COLOR_BGR2RGB)
            self.fig, self.ax = plt.subplots(figsize=(8, 6))
            self.ax.imshow(img_rgb)
            self.ax.set_title(f"{self.current_title} - Select ROI with mouse")
            self.rect_selector = RectangleSelector(
                self.ax,
                onselect=self.on_select,
                useblit=False,
                button=[1],
                minspanx=10,
                minspany=10,
                spancoords='pixels',
                interactive=True,
            )
            plt.show()

    def on_select(self, eclick, erelease):
        if any(v is None for v in (eclick.xdata, eclick.ydata, erelease.xdata, erelease.ydata)):
            return
        x1, y1, x2, y2 = map(int, (eclick.xdata, eclick.ydata, erelease.xdata, erelease.ydata))
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])
        cropped = self.current_image[y1:y2, x1:x2]
        if cropped.size > 0:
            self.current_image = cropped
            self._draw_with_selector()

    def rotate_image(self, _):
        if self.current_image is None:
            return
        self.current_image = cv2.rotate(self.current_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        with self.output:
            clear_output()
            self._draw_with_selector()

    def reset_display(self, _):
        if self.original_image is None:
            return
        self.current_image = self.original_image.copy()
        with self.output:
            clear_output()
            self._draw_with_selector()

    def save_crop(self, label: str):
        if self.current_image is None:
            return
        cond = self.condition_selector.value
        load = self.load_selector.value
        gray = np.mean(self.current_image, axis=-1).astype(np.float32)
        gray_norm = np.clip((255.0 - gray) / 255.0, 0.0, 1.0)
        self.saved_regions[label].append({'condition': cond, 'load': load, 'image': gray_norm})
        base = os.path.join(self.manager.cwd, self.date_folder)
        os.makedirs(os.path.join(base, cond), exist_ok=True)
        idx = len(self.saved_regions[label])
        path = os.path.join(base, cond, f"{label}_{cond}_{load}_{idx}.tiff")
        cv2.imwrite(path, (gray_norm * 255.0).astype(np.uint8))
        print(f" Saved {label} crop to: {path}")

    def save_K(self, _):
        self.save_crop("K")

    def save_C(self, _):
        self.save_crop("C")

    def export_to_dataframe(self, _):
        # Keep in sync with load_selector
        loads = {"neg": 0, "1e5": 1e5, "1.5e5": 1.5e5, "2e5": 2e5, "5e5": 5e5, "1e6": 1e6, "5e6": 5e6, "1e7": 1e7, "pos": 1e9}

        def organize(region_list):
            grouped = {c: {} for c in ["N1", "N2", "N3", "N4"]}
            for r in region_list:
                grouped[r['condition']][loads[r['load']]] = r['image']
            df = pd.DataFrame({c: [grouped[c].get(b) for b in sorted(loads.values())] for c in grouped})
            df["Bacterial Load"] = sorted(loads.values())
            return df

        df_K = organize(self.saved_regions["K"])
        df_C = organize(self.saved_regions["C"])

        df_K_flat, df_C_flat = df_K.copy(), df_C.copy()
        for c in ["N1", "N2", "N3", "N4"]:
            df_K_flat[c] = df_K[c].apply(lambda x: ','.join(map(str, x.flatten())) if x is not None else '')
            df_C_flat[c] = df_C[c].apply(lambda x: ','.join(map(str, x.flatten())) if x is not None else '')

        base = os.path.join(self.manager.cwd, self.date_folder)
        os.makedirs(base, exist_ok=True)
        df_K_flat.to_csv(os.path.join(base, "df_K.csv"), index=False)
        df_C_flat.to_csv(os.path.join(base, "df_C.csv"), index=False)

        with self.output:
            clear_output()
            print(" Exported DataFrames and saved as CSV:")
            display(df_K.head())
            display(df_C.head())

        self.df_K, self.df_C = df_K, df_C

    def run(self):
        if ImageViewerWithROI._last_root is not None:
            try:
                ImageViewerWithROI._last_root.close()
            except Exception:
                pass
        self._root = widgets.VBox([
            widgets.HTML(value="<h3>Interactive Image ROI Viewer</h3>"),
            self.dropdown,
            widgets.HBox([self.condition_selector, self.load_selector]),
            widgets.HBox([self.show_button, self.rotate_button, self.reset_button]),
            widgets.HBox([self.save_K_button, self.save_C_button, self.export_button]),
            self.output
        ])
        ImageViewerWithROI._last_root = self._root
        display(self._root)

# =========================
# ROIAnalyzerWidget
# =========================
class ROIAnalyzerWidget:
    _last_root = None

    def __init__(self, base_root_dir: str | None = None, manager: ImageFolderManager | None = None):
        # Default to the current working directory if not provided
        self.base_root_dir = base_root_dir or os.getcwd()
        self.manager = manager

        self.df_K = self.df_C = None
        self.folder_chooser = FileChooser(self.base_root_dir)
        self.folder_chooser.title = "<b> Select a dated folder (e.g., 2025-07-07)</b>"
        self.folder_chooser.show_only_dirs = True
        self.folder_chooser.use_dir_icons = False

        self.current_dir_label = widgets.HTML(value=f"<i>Analyzer base directory:</i><br>{self.base_root_dir}")
        self.label_selector = widgets.ToggleButtons(options=["K", "C"], description='Label:', button_style='info')
        self.load_button = widgets.Button(description="Load ROIs", button_style='success')
        self.use_manager_button = widgets.Button(description="Use Manager Working Dir", button_style='warning')

        self.output = widgets.Output()
        self.load_button.on_click(self.load_rois)
        self.use_manager_button.on_click(self.use_manager_dir)

        # Auto-sync when the Manager changes its working directory
        if self.manager is not None:
            try:
                self.manager.add_cwd_listener(self.set_base_root_dir)
            except Exception:
                pass

        self._root = None

    # ----- re-rooting -----
    def set_base_root_dir(self, path: str):
        # quick way to re-root the analyzer without rebuilding the whole app.
        self.base_root_dir = path
        self.current_dir_label.value = f"<i>Analyzer base directory:</i><br>{self.base_root_dir}"
        self.folder_chooser = FileChooser(self.base_root_dir)
        self.folder_chooser.title = "<b> Select a dated folder (e.g., 2025-07-07)</b>"
        self.folder_chooser.show_only_dirs = True
        self.folder_chooser.use_dir_icons = False
        if self._root is not None:
            # rebuild the visible section that holds the chooser
            self._root.children = (
                self._root.children[0],  # header
                self._root.children[1],  # hint
                self.current_dir_label,
                self.folder_chooser,
                self._root.children[4],  # label selector
                self._root.children[5],  # buttons box
                self._root.children[6],  # output
            )

    def use_manager_dir(self, _):
        if self.manager is not None:
            self.set_base_root_dir(self.manager.cwd)

    # ----- data loading/plotting -----
    def load_rois(self, _):
        with self.output:
            clear_output()
            folder = self.folder_chooser.selected_path
            if not folder:
                print("No folder selected.")
                return
            label = self.label_selector.value
            df = self._load_from_folder(folder, label)
            setattr(self, f"df_{label}", df)
            print(f" Loaded {label} band ROIs from: {folder}")
            self._plot_grid(df, f"{label} ROIs from {os.path.basename(folder)}")

    def _load_from_folder(self, base_dir: str, label: str) -> pd.DataFrame:
        conditions = ["N1", "N2", "N3", "N4"]
        loads = {"neg": 0, "1e5": 1e5, "1.5e5": 1.5e5, "2e5": 2e5, "5e5": 5e5, "1e6": 1e6, "5e6": 5e6, "1e7": 1e7, "pos": 1e9}
        data = {c: [] for c in conditions}
        for load_str in loads:
            for cond in conditions:
                folder = os.path.join(base_dir, cond)
                if not os.path.exists(folder):
                    data[cond].append(None)
                    continue
                pattern = f"{label}_{cond}_{load_str}_"
                matches = [f for f in os.listdir(folder) if f.startswith(pattern) and f.endswith(".tiff")]
                if matches:
                    img = cv2.imread(os.path.join(folder, matches[0]), cv2.IMREAD_GRAYSCALE)
                    data[cond].append((255.0 - img.astype(np.float32)) / 255.0 if img is not None else None)
                else:
                    data[cond].append(None)
        df = pd.DataFrame(data)
        df["Bacterial Load"] = list(loads.values())
        return df

    def _plot_grid(self, df: pd.DataFrame, title: str):
        fig, axs = plt.subplots(len(df), 4, figsize=(12, 2 * len(df)))
        for i, row in df.iterrows():
            for j, cond in enumerate(["N1", "N2", "N3", "N4"]):
                ax = axs[i, j]
                if row[cond] is not None:
                    ax.imshow(row[cond], cmap='gray', aspect='auto')
                ax.set_title(f"{cond} - {int(row['Bacterial Load'])}")
                ax.axis('off')
        plt.suptitle(title)
        plt.tight_layout()
        plt.show()

    def run(self):
        if ROIAnalyzerWidget._last_root is not None:
            try:
                ROIAnalyzerWidget._last_root.close()
            except Exception:
                pass
        self._root = widgets.VBox([
            widgets.HTML(value="<h3>ROI Reload and Viewer</h3>"),
            widgets.HTML(value="<i>Please select a dated folder containing subfolders N1–N4.</i>"),
            self.current_dir_label,
            self.folder_chooser,
            self.label_selector,
            widgets.HBox([self.use_manager_button, self.load_button]),
            self.output,
        ])
        ROIAnalyzerWidget._last_root = self._root
        display(self._root)

# =========================
# Instantiate & display
# =========================
def run_app():
    """Build and display the full UI."""
    manager = ImageFolderManager(); manager.run()
    viewer  = ImageViewerWithROI(manager); viewer.run()
    analyzer = ROIAnalyzerWidget(base_root_dir=os.getcwd(), manager=manager); analyzer.run()

if __name__ == "__main__":
    # optional: lets you test by running `python one_cell_app.py` in a notebook
    run_app()
