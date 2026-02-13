"""Settings GUI for RuSwitch (tkinter)."""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from config import Config
from dictionary import DictionaryManager

# Version
VERSION = '1.0.0'


class SettingsWindow:
    """Tabbed settings window."""

    def __init__(self, config: Config, dictionary: DictionaryManager,
                 on_save: Optional[callable] = None):
        self.config = config
        self.dictionary = dictionary
        self._on_save = on_save
        self._root: Optional[tk.Tk] = None

    def show(self) -> None:
        """Show the settings window (creates new Tk root if needed)."""
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return

        self._root = tk.Tk()
        self._root.title('RuSwitch Settings')
        self._root.geometry('500x400')
        self._root.resizable(False, False)

        notebook = ttk.Notebook(self._root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab: General
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text='General')
        self._build_general_tab(general_frame)

        # Tab: Dictionary
        dict_frame = ttk.Frame(notebook, padding=10)
        notebook.add(dict_frame, text='Dictionary')
        self._build_dictionary_tab(dict_frame)

        # Tab: About
        about_frame = ttk.Frame(notebook, padding=10)
        notebook.add(about_frame, text='About')
        self._build_about_tab(about_frame)

        # Buttons
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

        ttk.Label(parent, text='Manual remap hotkey:').grid(row=4, column=0, sticky=tk.W, pady=2)
        self._hotkey_manual_var = tk.StringVar(value=self.config.hotkey_manual)
        ttk.Entry(parent, textvariable=self._hotkey_manual_var,
                  width=15).grid(row=4, column=1, sticky=tk.W, pady=2)

        ttk.Label(parent, text='Toggle hotkey:').grid(row=5, column=0, sticky=tk.W, pady=2)
        self._hotkey_toggle_var = tk.StringVar(value=self.config.hotkey_toggle)
        ttk.Entry(parent, textvariable=self._hotkey_toggle_var,
                  width=15).grid(row=5, column=1, sticky=tk.W, pady=2)

        ttk.Label(parent, text='Excluded processes (one per line):').grid(
            row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 2))
        self._excluded_text = tk.Text(parent, height=4, width=40)
        self._excluded_text.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=2)
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
        # Parse "[RU] word" or "[EN] word"
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
