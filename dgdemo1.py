#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk, numpy as np
import datagrid as dg

# Demo data
x= np.linspace(-5,5,100)
# These are not functions but data sets:
datas= {"d_x": (x, x),
        "d_sin": (x, np.sin(x)),
        "d_cos": (x, np.cos(x)),
        "d_sample1": (x, np.random.random(len(x))),
        "d_sample2": (x, 1.5*np.random.random(len(x))),
        "d_sqrt(x+5)": (x, np.sqrt(x+5)),
        "d_x**2": (x, np.power(x/10,2)),
        "d_csili": (x, np.exp(-0.5*x)*np.sin(5*x)/3)
        }

win= tk.Tk()
win.option_add("*TkFDialog*foreground","black")
win.option_add("*TkFDialog*background","white")
win.columnconfigure(0, weight=1)
win.rowconfigure(0, weight=1)
win.wm_title("Data Grid Demo 1")

#app= dg.DataGrid(win, dataframe=datas, demo=False, toolbar=False)
app= dg.DataGrid(win, dataframe=datas, demo=True)

win.mainloop()
