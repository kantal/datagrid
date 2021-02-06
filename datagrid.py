#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""DataGrid

A Python Tkinter class for matplotlib grid where the layout can be changed with mouse clicks.

Copyright (c) 2021, Antal Koós
License: MIT

https://github.com/kantal/datagrid

Use:
    - middle mouse button: pop up grid menu (the main purpose of writing the program)
    - right mouse button: pop up dataset menu (additional dataset can be added)
    - left mouse button on a plot: pop up action menu (just an example)
"""

__version__= "0.9.2"

import tkinter as tk
from tkinter import ttk
from tkinter import colorchooser as tkcolorch
import time
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import cm
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
import numpy as np

STRECH= tk.N,tk.S,tk.E,tk.W
#--

class DataGrid(ttk.Frame):

    def __init__(self, wroot, dataframe, gridsize=(4,4), demo=False, toolbar=True, **kwargs):

        """ DataGrid

        Matplotlib 'axes' objects can be split and expanded on the grid specified by 'gridsize'.
        wroot: The parent window
        dataframe: A dict with 'name_string' --> (data_set_x, data_set_y)
        gridsize: The grid sizes as (width,height).
        demo: When True, a randomly selected dataset will be plotted on a newly created axes.
        toolbar: When True, the matplotlib toolbar will be rendered.
        kwargs: These args are passed to the base class.

        """
        super().__init__(wroot, **kwargs)

        self.df= dataframe
        self.wroot= wroot
        self.nrow, self.ncolumn= gridsize[0], gridsize[1] # mpl grid
        self.demo= demo

        """
        In constrained_layout mode, moving subplot triggers a warning and the figure will
        be wrong. Workaround: calling 'set_tight_layout(True)' when a subplot changes.
        """
        self.fig= plt.figure(constrained_layout=False)
        self.gs= self.fig.add_gridspec(self.nrow, self.ncolumn)

        self.canvas= FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw_idle()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=STRECH)

        if toolbar:
            # embed the mpl toolbar into a ttk.Frame
            self.toolbarFrame= ttk.Frame(master=self)
            self.mpl_toolbar= NavigationToolbar2Tk(self.canvas, self.toolbarFrame)

            # create a help button on the toolbar
            self.tw_help= None
            self.helpBtn= ttk.Button(self, text="Help", command=self.show_help)

            self.toolbarFrame.grid(row=1, column=0, sticky=tk.W)
            self.helpBtn.grid(row=1, column=0, sticky=tk.E)

        #place the main frame
        self.grid(sticky=STRECH)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        ax1= self.fig.add_subplot(self.gs[0:self.nrow//2,:])
        ax2= self.fig.add_subplot(self.gs[self.nrow//2:,:])
        if self.demo:
            self.showgraph(ax1, *self.demo_select())
            self.showgraph(ax2, *self.demo_select())

        self.fig.set_tight_layout(True)

        self.pick_hndl= self.canvas.mpl_connect('pick_event', self.on_pick)
        self.mousebutton_hndl= self.canvas.mpl_connect('button_press_event', self.on_press)

        self.topup_menu= []

        """
        dmfuncs: dict of grid menu funcs and labels

                - the keys are provided by 'get_nbrs()': 'top','right','bottom','left'
                - the values: (label text, label callback function for expanding the axes)
                or
                - the keys are 'vsplit' and 'hsplit'
                - the values: (label text, label callback function for splitting)
        """
        self.dmfuncs={  "top": ("extend upwards",self.extend),
                        "right": ("extend to the right",self.extend),
                        "bottom": ("extend downwards",self.extend),
                        "left": ("extend to the left",self.extend),
                        "hsplit": ("hsplit",self.split),
                        "vsplit": ("vsplit", self.split) }

        self.cnt=100
        """ cnt: serves as label for axes
        Without this, extending an axes to the left, or split it horizontally without
        labeling results in:
         'MatplotlibDeprecationWarning: Adding an axes using the same arguments as a
         previous axes currently reuses the earlier instance.  In a future version, a new
         instance will always be created and returned.  Meanwhile, this warning can be
         suppressed, and the future behavior ensured, by passing a unique label to each
         axes instance.'
        """

        self.style= ttk.Style()
        if toolbar:
            # set the background of the main frame to the background of mpl_toolbar
            self.style.configure("MainFrame.TFrame", background= self.mpl_toolbar["background"] )
            self.configure(style="MainFrame.TFrame")

        self.style.configure("MenuLabel.TLabel", padding=3)
        self.style.configure("MenuSeparator.TSeparator", background="black")

        self.picktime= time.monotonic()


    def on_press(self, msevent):
        """mpl mouse button event handler

        It is invoked after a pick event, too.
        """

        if not msevent.inaxes:
            self.menu_off(msevent)
            return

        if msevent.button==1:
            # Nothing to do, the pick event was handled.
            return

        elif msevent.button==3:

            self.menu_off(msevent)
            self.create_data_menu(msevent)

        elif msevent.button==2:

            self.menu_off(msevent)
            self._create_grid_menu(msevent)


    def on_pick(self, pickevent):
        """mpl pick event handler"""

        t= time.monotonic()
        if t-self.picktime <= 0.4:  # handle only the first event when there are more artists in the same place
            #print("ignore")
            return

        self.picktime= t
        self.menu_off(pickevent)
        if pickevent.mouseevent.button==1:
                self.create_action_menu(pickevent)


    def rc_geometry(self, ax):
        """
        return: r1,c1,r2,c2,rspan,cspan
        """
        nrow,ncol,start,stop= ax.get_subplotspec().get_geometry()
        r1,c1,r2,c2= start//ncol, start%ncol, stop//ncol, stop%ncol
        return r1,c1,r2,c2,r2-r1+1,c2-c1+1


    def get_nbrs(self, ax):
        """
        return: a dictionary of subplotspecs fitting on top, left, etc.
        """
        row1,col1,row2,col2,rspn,cspn= self.rc_geometry(ax)
        dnbrs={}

        for iax in self.fig.axes:

            if iax is not ax:

                r1,c1,r2,c2,rs,cs= self.rc_geometry(iax)
                if (cspn,row1-1,col1)==(cs,r2,c1):
                    dnbrs["top"]=iax
                elif (cspn,row2+1,col1)==(cs,r1,c1):
                    dnbrs["bottom"]=iax
                elif (rspn,row1,col2+1)==(rs,r1,c1):
                    dnbrs["right"]=iax
                elif (rspn,row1,col1-1)==(rs,r1,c2):
                    dnbrs["left"]=iax

            if len(dnbrs)==4:
                break

        return dnbrs


    def split(self,ax,hv):
        # vertical split

        row1,col1,row2,col2,rspn,cspn= self.rc_geometry(ax)
        if hv=="vsplit":

            if cspn<2:
                return

            cells1= self.gs[row1:row2+1,col1:col1+cspn//2]
            cells2= self.gs[row1:row2+1,col1+cspn//2:col2+1]

        elif hv=="hsplit":

            if rspn<2:
                return

            cells1= self.gs[row1:row1+rspn//2,col1:col2+1]
            cells2= self.gs[row1+rspn//2:row2+1,col1:col2+1]

        else:
            raise ValueError(f"How to split? ({hv})")
            return

        ax.set_position(cells1.get_position(self.fig))
        ax.set_subplotspec(cells1)   # refresh the geometry
        newax= self.fig.add_subplot(cells2, label=str(self.cnt))
        self.cnt+=1

        if self.demo:
            self.showgraph(newax, *self.demo_select())

        self.fig.set_tight_layout(True)
        self.fig.canvas.draw_idle()

        self.menu_off(None)


    def extend(self,ax,to):

        dn= self.get_nbrs(ax)
        axnbr= dn[to]
        nr1,nc1,nr2,nc2,nrs,ncs= self.rc_geometry(axnbr)
        axnbr.remove()

        row1,col1,row2,col2,rspn,cspn= self.rc_geometry(ax)
        if to=="left":
            cells= self.gs[row1:row2+1,nc1:col2+1]
        elif to=="right":
            cells= self.gs[row1:row2+1,col1:nc2+1]
        elif to=="top":
            cells= self.gs[nr1:row2+1,col1:col2+1]
        elif to=="bottom":
            cells= self.gs[row1:nr2+1,col1:col2+1]
        else:
            raise ValueError(f"How to extend? ({to})")
            return

        ax.set_position(cells.get_position(self.fig))
        ax.set_subplotspec(cells)   # refresh the geometry

        self.fig.set_tight_layout(True)
        self.fig.canvas.draw_idle()

        self.menu_off(None)


    def legend(self, ax):
        leg= ax.legend()
        leg.set_draggable(True)


    def showgraph(self,ax,key, gtype="p"):

        if gtype=="p":
            ax.plot(self.df[key][0],self.df[key][1], label=key, picker=True)
        elif gtype=="b":
            ax.bar(self.df[key][0],self.df[key][1], label=key, picker=True)
        else:
            ax.scatter(self.df[key][0],self.df[key][1], label=key, picker=True)

        self.legend(ax)
        self.fig.canvas.draw_idle()


    def _create_grid_menu(self,msevent):
        """ msevent: mpl mouseevent object """

        ax= msevent.inaxes
        self.tw_grid_menu, fr= self.menu_on(ax, "Grid Menu")

        dn= self.get_nbrs(ax)
        r1,c1,r2,c2,rspn,cspn= self.rc_geometry(ax)

        nentry=0    # number of menu entries
        self._gridmenulbls=[]
        if rspn>1:
            lb= ttk.Label(fr, text= self.dmfuncs["hsplit"][0], style="MenuLabel.TLabel")
            self._gridmenulbls.append(lb)
            # Tkinter event handler:
            lb.bind("<Button-1>", lambda event,ax=ax: self.dmfuncs["hsplit"][1](ax,"hsplit"))
            lb.grid(row=nentry)
            nentry+=1

        if cspn>1:
            lb= ttk.Label(fr, text= self.dmfuncs["vsplit"][0], style="MenuLabel.TLabel")
            self._gridmenulbls.append(lb)
            lb.bind("<Button-1>", lambda event,ax=ax: self.dmfuncs["vsplit"][1](ax,"vsplit"))
            lb.grid(row=nentry)
            nentry+=1

        sepa= ttk.Separator(fr,orient=tk.HORIZONTAL, style="MenuSeparator.TSeparator")
        sepa.grid(row=nentry, sticky=tk.W+tk.E)
        nentry+= 1

        nent= 0
        for pos in ["top","right","bottom","left"]:

            if pos in dn:
                lb=  ttk.Label(fr, text= self.dmfuncs[pos][0], style="MenuLabel.TLabel")
                self._gridmenulbls.append(lb)
                lb.bind("<Button-1>", lambda event,ax=ax,pos=pos: self.dmfuncs[pos][1](ax,pos))
                lb.grid(row=nentry+nent)
                nent+= 1

        if nentry==0 or nent==0:
            sepa.grid_forget()

        self.place_tw(self.tw_grid_menu, msevent) # set the position of the window
        self.tw_grid_menu.protocol("WM_DELETE_WINDOW", lambda: self.menu_off(None))

    #--
    def create_data_menu(self, msevent):
        """ Provide dataset selection menu

        msevent: a matplotlib mouseevent object
        This method can be overwritten, but the head and tail parts are worth keeping.
        The selected dataset can be plotted by 'self.showgraph(ax,name,pt)', where
        - 'ax':  the axes on which the clicked occurred
        - 'name': the dataset name, i.e. the key in the data frame
        - 'pt': the plot type: 'p' line, 'b' bar, 's' scatter
        The the dataframe can be accessed with the variable 'self.df'.
        Other usefull attributes:
            - self.wroot: the parent window of DataGrid object
            - self.nrow, self.ncolumn: the grid size
        """

        #-- Head
        ax= msevent.inaxes
        self.tw_data_menu, fr= self.menu_on(ax, "Data Menu")

        #-- Middle
        ldfk= list(self.df.keys())
        entry_text= tk.StringVar()
        entry_text.set(ldfk[0])
        cbox= ttk.Combobox(fr, textvariable=entry_text, values=ldfk, justify=tk.CENTER)

        for ii,(ptname,pt) in enumerate([("plot","p"),("bar","b"),("scatter","s")]):

                lb= ttk.Label(fr, text=ptname, style="MenuLabel.TLabel")
                lb.bind("<Button-1>",
                        lambda event,pt=pt: self.showgraph(ax,entry_text.get(),pt))
                lb.grid(row=0, column=ii)

        cbox.grid(row=1, column=0, columnspan=ii+1)

        #-- Tail
        self.place_tw(self.tw_data_menu, msevent)
        self.tw_data_menu.protocol("WM_DELETE_WINDOW", lambda: self.menu_off(None))

    #--
    def create_action_menu(self, pickevent):
        """ Provide a menu for changing plot properties."""

        artist= pickevent.artist
        if not isinstance(artist, (mpl.lines.Line2D, mpl.collections.PathCollection, mpl.patches.Rectangle)):
            return

        ax= artist.axes
        self.tw_action_menu, fr= self.menu_on(ax, "Action Menu")

        #--
        def remove(artist, ax):
            artist.remove()
            self.legend(ax)
            ax.figure.canvas.draw_idle()
            self.menu_off(None)


        def getcolor(artist, ax):
            # line:
            if isinstance(artist, mpl.lines.Line2D):
                return artist.get_color()
            # scatter:
            if isinstance(artist, mpl.collections.PathCollection):
                return artist.get_facecolor()[0]
            # bar:
            if isinstance(artist, mpl.patches.Rectangle):
                return artist.get_facecolor()

            raise ValueError("what kind of artist?")


        def setcolor(artist, ax, plotnm, ocolor):

            c= tkcolorch.askcolor(ocolor, title=plotnm)[1]
            self.menu_off(None)
            if c==None:
                return

            if isinstance(artist, mpl.lines.Line2D):
                artist.set_color(c)
            # scatter:
            elif isinstance(artist, mpl.collections.PathCollection):
                artist.set_facecolor(c)
            # bar:
            elif isinstance(artist, mpl.container.BarContainer):
                for r in artist:
                    r.set_facecolor(c)

            self.legend(ax)

        #--
        oldcolor= mpl.colors.to_hex(getcolor(artist, ax))

        if isinstance(artist,mpl.patches.Rectangle):
            for cont in ax.containers:
                if artist in cont:
                    artist= cont
                    break

        plotname= artist.get_label()
        ttk.Label(fr, text=plotname, style="MenuLabel.TLabel", foreground=oldcolor).grid(row=0, column=0, columnspan=3)
        ttk.Button(fr, text="✖ Remove", command=lambda: remove(artist,ax)).grid(row=1,column=0)
        ttk.Button(fr,text="Color", command=lambda: setcolor(artist, ax, plotname, oldcolor)).grid(row=1,column=1)
        ttk.Button(fr,text="Cancel", command=lambda: self.menu_off(None)).grid(row=1,column=2)

        #--
        self.place_tw(self.tw_action_menu, pickevent.mouseevent)
        self.tw_action_menu.protocol("WM_DELETE_WINDOW", lambda: self.menu_off(None))

    #--
    def demo_select(self):
        return np.random.choice(list(self.df.keys())), "p"

    #--
    def show_help(self, text=__doc__):

        if self.tw_help:
            return

        self.tw_help= tk.Toplevel(self)
        self.tw_help.transient(self)
        self.tw_help.wm_title("Help")
        self.tw_help.columnconfigure(0,weight=1)
        self.tw_help.rowconfigure(0,weight=1)

        fr= ttk.Frame(self.tw_help)
        fr.grid(sticky=STRECH)

        htext= tk.Text(fr, wrap=tk.WORD)
        vscr= ttk.Scrollbar(fr, orient=tk.VERTICAL, command=htext.yview)
        htext['yscrollcommand']= vscr.set

        htext.grid(row=0,column=0,columnspan=2, sticky=STRECH)
        vscr.grid(row=0, column=2, sticky=tk.N+tk.S)
        fr.columnconfigure(0,weight=1)
        fr.rowconfigure(0,weight=1)

        htext.insert("1.0", text)
        htext["state"]= "disabled"

        def help_off(event=None):
            self.tw_help.destroy()
            self.tw_help= None

        self.tw_help.protocol("WM_DELETE_WINDOW", help_off)


    def menu_on(self, ax, title):

        self.topup_menu[:]= [ax, ax.get_facecolor()]
        ax.set_facecolor("lightgrey")
        self.fig.canvas.draw_idle()

        #Creates a toplevel window with a frame inside
        tw= tk.Toplevel(self)
        tw.resizable(False,False)
        tw.transient(self)
        tw.wm_title(title)
        fr= ttk.Frame(tw)
        fr.grid()
        self.topup_menu.append(tw)

        return tw,fr


    def menu_off(self, event):

        if self.topup_menu:

            ax, fc, tw= self.topup_menu
            self.topup_menu[:]= []
            tw.destroy()
            ax.set_facecolor(fc)
            self.fig.canvas.draw_idle()


    def place_tw(self, tw, event):
        """Places the upper-left corner of the window where the clicked occurred"""

        x,y= event.guiEvent.x, event.guiEvent.y
        xx,yy= self.wroot.winfo_x(), self.wroot.winfo_y()
        tw.geometry(f"+{xx+x}+{yy+y}")

#---
if __name__ == "__main__":
    print(f"datagrid.py, version {__version__}")

