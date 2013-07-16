#!/usr/bin/env python3

# Copyright (c) 2013 David Munger
# 
# This file is part of Rembobine.
# 
# Rembobine is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Rembobine is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Rembobine.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk, GLib
import subprocess
import re
import os

# localization
APP = 'rembobine'
DIR = os.path.join(GLib.get_user_data_dir(), 'locale')
import locale
import gettext
locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)
_ = gettext.gettext


class AppWindow(Gtk.ApplicationWindow):

    def __init__(self, app):
        Gtk.ApplicationWindow.__init__(self,
                title=_("{} - Convert a video").format(APP),
                application=app)

        infile = self.get_application().infile
        outfile = self.get_application().outfile

        self.requested_outfile = outfile
        self.crf_min = 40
        self.crf_max = 20

        grid = Gtk.Grid(column_spacing=10, row_spacing=20, border_width=20,
                expand=True, column_homogeneous=True)
        grid.set_size_request(400, 100)
        self.add(grid)

        # input file
        dialog = Gtk.FileChooserDialog(_("Select a video file to convert"), self,
                Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        self.add_file_filters(dialog)

        label = Gtk.Label(_("Input video file"), halign=Gtk.Align.END)
        self.input_file = Gtk.FileChooserButton(action=Gtk.FileChooserAction.OPEN, dialog=dialog)
        self.input_file.connect('selection-changed', self.on_input_file_changed)
        grid.attach(label,           0, 0, 1, 1)
        grid.attach(self.input_file, 1, 0, 1, 1)

        # information
        label = Gtk.Label(_("Information"), halign=Gtk.Align.END)
        self.information = Gtk.Label()
        grid.attach(label,            0, 1, 1, 1)
        grid.attach(self.information, 1, 1, 1, 1)

        # resolution
        label = Gtk.Label(_("Resolution"), halign=Gtk.Align.END)
        store = Gtk.ListStore(str, str, str)
        store.append([_("original"), '', ''])
        store.append([_("1080p"),   '1920x1080',    '16:9'])
        store.append([_("720p"),    '1280x720',     '16:9'])
        store.append([_("480p"),    '854x480',      '16:9'])
        store.append([_("large"),   '1024x768',     '4:3'])
        store.append([_("medium"),  '800x600',      '4:3'])
        store.append([_("small"),   '640x480',      '4:3'])
        store.append([_("iPod"),    '320x240',      '4:3'])
        self.resolution = Gtk.ComboBox.new_with_model(store)
        for col in range(3):
            renderer_text = Gtk.CellRendererText()
            self.resolution.pack_start(renderer_text, True)
            self.resolution.add_attribute(renderer_text, "text", col)
        self.resolution.set_active(0)
        grid.attach(label,           0, 2, 1, 1)
        grid.attach(self.resolution, 1, 2, 1, 1)

        # quality
        label = Gtk.Label(_("Quality"), halign=Gtk.Align.END)
        self.quality = Gtk.Adjustment(75, 0, 100, 1, 10, 0)
        scale = Gtk.Scale(adjustment=self.quality, draw_value=True, digits=0)
        #scale = Gtk.SpinButton(adjustment=self.quality, numeric=True)
        grid.attach(label, 0, 3, 1, 1)
        grid.attach(scale, 1, 3, 1, 1)

        # rotation
        label = Gtk.Label(_("Rotation"), halign=Gtk.Align.END)
        store = Gtk.ListStore(str, str)
        store.append([_("no rotation"), ''])
        store.append([_("90° right"),   '1'])
        store.append([_("90° left"),    '2'])
        self.rotation = Gtk.ComboBox.new_with_model(store)
        for col in range(1):
            renderer_text = Gtk.CellRendererText()
            self.rotation.pack_start(renderer_text, True)
            self.rotation.add_attribute(renderer_text, "text", col)
        self.rotation.set_active(0)
        grid.attach(label,           0, 4, 1, 1)
        grid.attach(self.rotation,   1, 4, 1, 1)

        # actions
        box = Gtk.Box()
        grid.attach_next_to(box, label, Gtk.PositionType.BOTTOM, 2, 1)
        button = Gtk.Button(label=Gtk.STOCK_CANCEL, use_stock=True,
                always_show_image=True)
        button.connect('clicked', self.on_cancel)
        box.pack_start(button, True, True, 5)
        button = Gtk.Button(label=Gtk.STOCK_CONVERT, use_stock=True,
                always_show_image=True)
        button.connect('clicked', self.on_convert)
        box.pack_start(button, True, True, 5)
        button.set_sensitive(False)
        self.convert_button = button

        self.progress = Gtk.ProgressBar(show_text=True)
        grid.attach_next_to(self.progress, box, Gtk.PositionType.BOTTOM, 2, 1)

        self.mencoder_process = None

        if infile:
            self.input_file.set_filename(infile)

    def on_input_file_changed(self, widget):
        infile = self.input_file.get_filename()
        self.convert_button.set_sensitive(infile is not None)
        if infile:
            info = self.identify(infile)
            self.information.set_markup('<b>{VIDEO_CODEC}/{AUDIO_CODEC}</b>, {VIDEO_WIDTH}x{VIDEO_HEIGHT}, <i>{VIDEO_FPS} fps</i>'.format(**info))

    def on_cancel(self, widget):
        if self.mencoder_process:
            self.mencoder_process.terminate()
        self.get_application().quit()

    def on_convert(self, widget):
        dialog = Gtk.FileChooserDialog(
                _("Save as..."),
                self,
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))

        # set directory
        infile = self.input_file.get_filename()
        dialog.set_current_folder(os.path.dirname(infile))
        if self.requested_outfile:
            dialog.set_current_folder(os.path.dirname(self.requested_outfile))
            dialog.set_current_name(os.path.basename(self.requested_outfile))
        else:
            dialog.set_current_name(os.path.basename(infile + '.avi'))

        self.add_file_filters(dialog)

        response = dialog.run()
        outfile = None
        if response == Gtk.ResponseType.ACCEPT:
            outfile = dialog.get_filename()

        dialog.destroy()

        if outfile:
            self.convert_button.set_sensitive(False)
            self.convert(outfile)

    def add_file_filters(self, dialog):
        filt = Gtk.FileFilter()
        filt.set_name("Vidéos")
        filt.add_mime_type("video/quicktime")
        filt.add_mime_type("video/mp4")
        filt.add_mime_type("video/x-msvideo")
        dialog.add_filter(filt)

        filt = Gtk.FileFilter()
        filt.set_name("Tout fichier")
        filt.add_pattern("*")
        dialog.add_filter(filt)

    def convert(self, outfile):

        infile = self.input_file.get_filename()
        resolution = self.resolution.get_active_iter()
        rotation = self.rotation.get_active_iter()
        filters = []

        if resolution:
            resolution = self.resolution.get_model()[resolution][1]
            if resolution:
                filters.append('scale={}:{}'.format(*resolution.split('x')))

        if rotation:
            rotation = self.rotation.get_model()[rotation][1]
            if rotation:
                filters.append('rotate={}'.format(rotation))

        crf = self.crf_min + (self.crf_max - self.crf_min) \
                * self.quality.get_value() / 100

        # construct command line
        cmd = ['mencoder', infile, '-o', outfile,
                '-oac', 'mp3lame',
                '-ovc', 'x264', '-x264encopts',
                'crf={}:threads=auto'.format(crf)]
        if filters:
            cmd += ['-vf', ','.join(filters)]
        print(' '.join('"{}"'.format(x) for x in cmd))
        self.mencoder_process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, bufsize=80)

        # parse output
        line = ''
        pat = re.compile(r'\(\s*(\d+)\s*%\).*\s+([0-9]+)min\s.*\s+([0-9]+)mb\s')
        while True:
            out = self.mencoder_process.stdout.read(80)
            if not out:
                break
            line += out.decode()
            line = line.split('\r')[-1]
            m = re.search(pat, line)
            if m:
                self.set_progress(float(m.group(1)) / 100, m.group(2), m.group(3))
        self.get_application().quit()

    def set_progress(self, fraction, time, size):
        self.progress.set_fraction(fraction)
        self.progress.set_text('{} %  ({} Mo)'.format(int(100 * fraction), size))
        while Gtk.events_pending():
            Gtk.main_iteration()

    def identify(self, filename):
        cmd = ['mplayer', '-frames', '0', '-vo', 'null', '-ao', 'null',
                '-identify', filename]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        info = {}
        pat = re.compile(r'^ID_([^=]+)=(.*)')
        for line in output.decode().split('\n'):
            m = pat.match(line)
            if m:
                info[m.group(1)] = m.group(2)
        return info

class RembobineApplication(Gtk.Application):
    def __init__(self, infile=None, outfile=None):
        Gtk.Application.__init__(self)
        self.infile = infile
        self.outfile = outfile

    def do_activate(self):
        win = AppWindow(self)
        win.show_all()

    def do_startup(self):
        Gtk.Application.do_startup(self)

if __name__ == '__main__':
    import sys
    infile = outfile = None
    if len(sys.argv) > 1:
        infile = sys.argv[1]
    if len(sys.argv) > 2:
        outfile = sys.argv[2]
    app = RembobineApplication(infile, outfile)
    exit_status = app.run([]) #sys.argv)
    sys.exit(exit_status)
