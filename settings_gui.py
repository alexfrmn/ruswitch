"""Settings GUI for RuSwitch (tkinter)."""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from config import Config
from dictionary import DictionaryManager

VERSION = '1.2.0'

# Modifier keysyms (tkinter names)
_MODIFIER_KEYSYMS = {
    'control_l', 'control_r', 'alt_l', 'alt_r',
    'shift_l', 'shift_r', 'super_l', 'super_r',
    'meta_l', 'meta_r',
}

# Map tkinter keysym → keyboard library name
_KEYSYM_MAP = {
    'insert': 'insert', 'delete': 'delete',
    'home': 'home', 'end': 'end',
    'prior': 'page up', 'next': 'page down',
    'pause': 'pause', 'scroll_lock': 'scroll lock',
    'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4',
    'f5': 'f5', 'f6': 'f6', 'f7': 'f7', 'f8': 'f8',
    'f9': 'f9', 'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
    'escape': 'esc', 'return': 'enter', 'space': 'space',
    'backspace': 'backspace', 'tab': 'tab',
}


class HotkeyButton(ttk.Button):
    """A button that captures the next keypress as a hotkey.

    Tracks modifier keys explicitly via KeyPress/KeyRelease instead of
    relying on event.state (which has phantom bits on Windows).
    """

    def __init__(self, parent, variable: tk.StringVar, **kwargs):
        self._variable = variable
        self._listening = False
        self._held_modifiers: set[str] = set()
        super().__init__(parent, text=variable.get(), command=self._start_listen,
                         width=18, **kwargs)
        self._variable.trace_add('write', self._on_var_change)

    def _on_var_change(self, *_args):
        if not self._listening:
            self.configure(text=self._variable.get())

    def _start_listen(self):
        """Start listening for a key press."""
        self._listening = True
        self._held_modifiers.clear()
        self.configure(text='[ Press a key... ]')
        top = self.winfo_toplevel()
        top.bind('<KeyPress>', self._on_key_down)
        top.bind('<KeyRelease>', self._on_key_up)

    def _on_key_down(self, event):
        """Track modifier presses; capture non-modifier key."""
        keysym = event.keysym.lower()

        # Track modifier keys
        if keysym in ('control_l', 'control_r'):
            self._held_modifiers.add('ctrl')
            return 'break'
        if keysym in ('alt_l', 'alt_r'):
            self._held_modifiers.add('alt')
            return 'break'
        if keysym in ('shift_l', 'shift_r'):
            self._held_modifiers.add('shift')
            return 'break'
        if keysym in ('super_l', 'super_r', 'meta_l', 'meta_r'):
            return 'break'

        # Non-modifier key — finalize the hotkey
        self._finalize(keysym)
        return 'break'

    def _on_key_up(self, event):
        """Track modifier releases."""
        keysym = event.keysym.lower()
        if keysym in ('control_l', 'control_r'):
            self._held_modifiers.discard('ctrl')
        elif keysym in ('alt_l', 'alt_r'):
            self._held_modifiers.discard('alt')
        elif keysym in ('shift_l', 'shift_r'):
            self._held_modifiers.discard('shift')
        return 'break'

    def _finalize(self, keysym: str):
        """Build hotkey string and stop listening."""
        top = self.winfo_toplevel()
        top.unbind('<KeyPress>')
        top.unbind('<KeyRelease>')
        self._listening = False

        # Translate keysym to keyboard library format
        key = _KEYSYM_MAP.get(keysym, keysym)

        # Build combo: modifiers (sorted) + key
        parts = sorted(self._held_modifiers)  # ctrl, alt, shift order
        parts.append(key)

        hotkey = '+'.join(parts)
        self._variable.set(hotkey)
        self.configure(text=hotkey)


class SettingsWindow:
    """Tabbed settings window."""

    def __init__(self, config: Config, dictionary: DictionaryManager,
                 on_save: Optional[callable] = None):
        self.config = config
        self.dictionary = dictionary
        self._on_save = on_save
        self._root: Optional[tk.Tk] = None

    def show(self) -> None:
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return

        self._root = tk.Tk()
        self._root.title('RuSwitch Settings')
        self._root.geometry('500x450')
        self._root.resizable(False, False)

        notebook = ttk.Notebook(self._root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text='General')
        self._build_general_tab(general_frame)

        dict_frame = ttk.Frame(notebook, padding=10)
        notebook.add(dict_frame, text='Dictionary')
        self._build_dictionary_tab(dict_frame)

        about_frame = ttk.Frame(notebook, padding=10)
        notebook.add(about_frame, text='About')
        self._build_about_tab(about_frame)

        btn_frame = ttk.Frame(self._root)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text='Save', command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text='Cancel', command=self._root.destroy).pack(side=tk.RIGHT)

        self._root.mainloop()

    def _build_general_tab(self, parent: ttk.Frame) -> None:
        self._auto_var = tk.BooleanVar(value=self.config.auto_mode)
        ttk.Checkbutton(parent, text='Auto-correction enabled',
                        variable=self._auto_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        self._notif_var = tk.BooleanVar(value=self.config.show_notification)
        ttk.Checkbutton(parent, text='Show notifications',
                        variable=self._notif_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(parent, text='Min word length:').grid(row=2, column=0, sticky=tk.W, pady=2)
        self._min_len_var = tk.IntVar(value=self.config.min_word_length)
        ttk.Spinbox(parent, from_=1, to=10, textvariable=self._min_len_var,
                     width=5).grid(row=2, column=1, sticky=tk.W, pady=2)

        ttk.Label(parent, text='Auto-learn threshold:').grid(row=3, column=0, sticky=tk.W, pady=2)
        self._threshold_var = tk.IntVar(value=self.config.auto_learn_threshold)
        ttk.Spinbox(parent, from_=1, to=20, textvariable=self._threshold_var,
                     width=5).grid(row=3, column=1, sticky=tk.W, pady=2)

        # Hotkey buttons with key capture
        ttk.Label(parent, text='Manual remap hotkey:').grid(row=4, column=0, sticky=tk.W, pady=4)
        self._hotkey_manual_var = tk.StringVar(value=self.config.hotkey_manual)
        HotkeyButton(parent, self._hotkey_manual_var).grid(
            row=4, column=1, sticky=tk.W, pady=4)

        ttk.Label(parent, text='Toggle hotkey:').grid(row=5, column=0, sticky=tk.W, pady=4)
        self._hotkey_toggle_var = tk.StringVar(value=self.config.hotkey_toggle)
        HotkeyButton(parent, self._hotkey_toggle_var).grid(
            row=5, column=1, sticky=tk.W, pady=4)

        ttk.Label(parent, text='(Click button, then press desired key)',
                  foreground='gray').grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=2)

        ttk.Label(parent, text='Excluded processes (one per line):').grid(
            row=7, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        self._excluded_text = tk.Text(parent, height=4, width=40)
        self._excluded_text.grid(row=8, column=0, columnspan=2, sticky=tk.W, pady=2)
        self._excluded_text.insert('1.0', '\n'.join(self.config.excluded_processes))

    def _build_dictionary_tab(self, parent: ttk.Frame) -> None:
        stats = self.dictionary.stats
        ttk.Label(parent, text=f'Base dictionaries: {stats["ru_base"]:,} RU / '
                  f'{stats["en_base"]:,} EN words').pack(anchor=tk.W, pady=2)
        ttk.Label(parent, text=f'User words: {stats["ru_user"]} RU / '
                  f'{stats["en_user"]} EN').pack(anchor=tk.W, pady=2)
        ttk.Label(parent, text=f'Words being learned: {stats["learning"]}').pack(
            anchor=tk.W, pady=2)

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Label(parent, text='User words:').pack(anchor=tk.W)

        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._word_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self._word_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._word_listbox.yview)

        for lang in ('ru', 'en'):
            for w in self.dictionary.get_user_words(lang):
                self._word_listbox.insert(tk.END, f'[{lang.upper()}] {w}')

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text='Add...', command=self._add_word_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='Remove', command=self._remove_word).pack(side=tk.LEFT, padx=2)

    def _build_about_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text='RuSwitch', font=('TkDefaultFont', 16, 'bold')).pack(pady=10)
        ttk.Label(parent, text=f'Version {VERSION}').pack()
        ttk.Label(parent, text='Automatic keyboard layout switcher').pack(pady=5)
        ttk.Label(parent, text='Punto Switcher alternative').pack()
        ttk.Label(parent, text='github.com/alexfrmn/ruswitch',
                  foreground='blue', cursor='hand2').pack(pady=10)

        # Log location
        import os
        from pathlib import Path
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            log_path = Path(appdata) / 'RuSwitch' / 'logs' / 'ruswitch.log'
        else:
            log_path = Path.home() / '.config' / 'ruswitch' / 'logs' / 'ruswitch.log'
        ttk.Label(parent, text=f'Log: {log_path}',
                  foreground='gray', wraplength=450).pack(pady=5)

    def _add_word_dialog(self) -> None:
        dialog = tk.Toplevel(self._root)
        dialog.title('Add Word')
        dialog.geometry('300x120')
        dialog.transient(self._root)
        dialog.grab_set()

        ttk.Label(dialog, text='Word:').grid(row=0, column=0, padx=5, pady=5)
        word_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=word_var, width=20).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text='Language:').grid(row=1, column=0, padx=5, pady=5)
        lang_var = tk.StringVar(value='ru')
        ttk.Combobox(dialog, textvariable=lang_var, values=['ru', 'en'],
                     state='readonly', width=5).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        def do_add():
            w = word_var.get().strip()
            if w:
                lang = lang_var.get()
                self.dictionary.add_word(w, lang)
                self._word_listbox.insert(tk.END, f'[{lang.upper()}] {w}')
                dialog.destroy()

        ttk.Button(dialog, text='Add', command=do_add).grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)

    def _remove_word(self) -> None:
        sel = self._word_listbox.curselection()
        if not sel:
            return
        item = self._word_listbox.get(sel[0])
        lang = item[1:3].lower()
        word = item[5:]
        self.dictionary.remove_word(word, lang)
        self._word_listbox.delete(sel[0])

    def _save(self) -> None:
        self.config.auto_mode = self._auto_var.get()
        self.config.show_notification = self._notif_var.get()
        self.config.min_word_length = self._min_len_var.get()
        self.config.auto_learn_threshold = self._threshold_var.get()
        self.config.hotkey_manual = self._hotkey_manual_var.get().strip()
        self.config.hotkey_toggle = self._hotkey_toggle_var.get().strip()
        excluded = self._excluded_text.get('1.0', tk.END).strip().splitlines()
        self.config.excluded_processes = [p.strip() for p in excluded if p.strip()]
        self.config.save()
        if self._on_save:
            self._on_save()
        self._root.destroy()
