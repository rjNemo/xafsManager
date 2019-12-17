import zmq
import os, sys
import numpy as np
from scipy.optimize import curve_fit
from scipy.interpolate import LSQUnivariateSpline
from scipy.ndimage import gaussian_filter1d
from scipy.integrate import simps
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from time import time

FPS_LIMIT = 10
EXAFS_SLOWDOWN_FACTOR = 10

class ZeroMQ_Listener(QtCore.QObject):
    message = QtCore.pyqtSignal(list)    
    def __init__(self):       
        QtCore.QObject.__init__(self)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect ("tcp://127.0.0.1:6400") 
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.running = True
        
    def loop(self):
        buf = []
        t0 = time()
        while self.running:
            try:
                string = self.socket.recv()
                buf.append(string)
                if time() - t0 > 1./FPS_LIMIT:
                    self.message.emit(buf[:]) 
                    buf = []
                    t0 = time()
            except:
                pass

    def finish(self):        
        self.socket.close()
        self.context.term()
                            
        
class EXAFS_Extractor(QtCore.QObject):
    message = QtCore.pyqtSignal(list)    
    def __init__(self):       
        QtCore.QObject.__init__(self)
        self.running = True
        self.pre1 = -150
        self.pre2 = -50
        self.post1 = 50
        
    def victoreen(self, e, c ,d):
        f = 1.23986e4/e
        return c*f**3 - d*f**4         
        
    def find_e0_idx(self, e, mu):
        d = gaussian_filter1d(np.gradient(mu) / np.gradient(e), 3)
        return np.argmax(d), d      
        
    def pre_edge(self, e, idx, mu):
        idx1 = np.abs(e[idx] + self.pre1 - e).argmin()  
        idx2 = np.abs(e[idx] + self.pre2 - e).argmin() 
        popt, pcov = curve_fit(self.victoreen, e[idx1:idx2], mu[idx1:idx2])
        return self.victoreen(e, popt[0], popt[1])
        
    def post_edge(self, e, idx, mu, pre, kw = 2):
        # k indexes starts from e0
        f = 0.262467 # magic number for calculation of k
        k = np.sqrt(f * (e[idx:]-e[idx]))
        kmin_idx = np.abs(e[idx] + self.post1 - e).argmin() - idx
        fun_fit = (mu[idx:] - pre[idx:]) * k**kw
        n_knots = int(2.0*(k.max() - k.min() ) / np.pi) + 1
        knots = np.linspace(k[kmin_idx], k[-2], n_knots)
        spl = LSQUnivariateSpline(k, fun_fit, knots)
        post = spl(k[kmin_idx:])/(k[kmin_idx:])**kw 
        edge_step = post[0]
        norm = mu - pre
        norm[idx + kmin_idx:] += -post + edge_step
        norm /= edge_step
        chi = norm[idx:] - 1
        return k, gaussian_filter1d(chi*k*k, 3)

    def hann_win(self, k, kmin, kmax, dk):
        win = np.empty_like(k)
        for i in range (len(k)):
            if (k[i] < (kmin - 0.5*dk)): 
                win[i] = 0.0
            elif (k[i] >= (kmin - 0.5*dk)) and (k[i] <= (kmin + 0.5*dk)): 
                win[i] = 0.5*(1.0 - np.cos(np.pi*(k[i] - kmin + 0.5*dk)/dk ) )
            elif (k[i] > (kmin + 0.5*dk)) and (k[i] < (kmax - 0.5*dk)): 
                win[i] = 1.0
            elif (k[i] >= (kmax - 0.5*dk)) and (k[i] <= (kmax + 0.5*dk)): 
                win[i] = 0.5*(1.0 + np.cos(np.pi*(k[i] - kmax + 0.5*dk)/dk ) )
            elif (k[i] >(kmax + 0.5*dk)):
                win[i] = 0.0
        return win    

    def make_ft(self, k, chi, r):
        ft_im = np.empty_like(r)
        ft_re = np.empty_like(r)
        ft_mag = np.empty_like(r)
        win = self.hann_win(k, 2.0, max(k) - 1., 1.0)  
        for i in range (len(r)):
	        ft_im[i] = simps (np.sin(2.0*k*r[i])*chi*win, k)
	        ft_re[i] = simps (np.cos(2.0*k*r[i])*chi*win, k)
	        ft_mag[i] = 1.0/np.sqrt(np.pi)*np.sqrt((ft_im[i]*ft_im[i] + ft_re[i]*ft_re[i])) 
        return ft_mag
        
    def calculate(self, list_data):
        e, mu1, mu2 = np.array(list_data[0]), np.array(list_data[1]), np.array(list_data[2]) 
        e0_idx1, e0_idx2, deriv1, deriv2 = None, None, [], []  
        try:
            e0_idx1, deriv1 = self.find_e0_idx(e, mu1)
            pre_edge1 = self.pre_edge(e, e0_idx1, mu1)
            k1, chi1 = self.post_edge(e, e0_idx1, mu1, pre_edge1)
        except:
            k1, chi1 = [], []
        try:
            e0_idx2, deriv2 = self.find_e0_idx(e, mu2)
            pre_edge2 = self.pre_edge(e, e0_idx2, mu2)
            k2, chi2 = self.post_edge(e, e0_idx2, mu2, pre_edge2)
        except:
            k2, chi2 = [], []
        r1, ft_mag1, r2, ft_mag2 = [], [], [], []
        if len(k1) > 0: 
            try:
                r1 = np.arange(0.0, 6.0, 0.02)
                ft_mag1 = self.make_ft(k1, chi1, r1)
            except:
                r1, ft_mag1 = [], []
        if len(k2) > 0: 
            try:
                r2 = np.arange(0.0, 6.0, 0.02)
                ft_mag2 = self.make_ft(k2, chi2, r2)
            except:
                r2, ft_mag2 = [], []
        self.message.emit([e0_idx1, deriv1, k1, chi1, r1, ft_mag1, e0_idx2, deriv2, k2, chi2, r2, ft_mag2, e])

class MonitorWidget(QtGui.QWidget):
    message_data = QtCore.pyqtSignal(list) 
    def __init__(self, app):
        QtGui.QWidget.__init__(self)
        self.app = app
        
        self.thread = QtCore.QThread()
        self.zeromq_listener = ZeroMQ_Listener()
        self.zeromq_listener.moveToThread(self.thread)        
        self.thread.started.connect(self.zeromq_listener.loop)
        self.zeromq_listener.message.connect(self.signal_received)        
        QtCore.QTimer.singleShot(0, self.thread.start)
        
        self.thread2 = QtCore.QThread()
        self.exafs_extractor = EXAFS_Extractor()
        self.exafs_extractor.moveToThread(self.thread2)        
        self.exafs_extractor.message.connect(self.update_exafs)        
        self.message_data.connect(self.exafs_extractor.calculate)   
        QtCore.QTimer.singleShot(1, self.thread2.start)
        
        self.layout = QtGui.QGridLayout()
        self.pw1 = pg.PlotWidget(title='I0 [counts] / Energy[eV]') 
        self.pw2 = pg.PlotWidget(title='I1 [counts] / Energy[eV]') 
        self.pw3 = pg.PlotWidget(title='I2 [counts] / Energy[eV]') 
        self.pw4 = pg.PlotWidget(title='IP [counts] / Energy[eV]')
        
        self.hbl = QtGui.QHBoxLayout()
        self.flabel = QtGui.QLabel("N/A")
        self.flabel.setStyleSheet("color: #fff")
        self.fbtn = QtGui.QPushButton("Open data folder")
        self.fbtn.clicked.connect(self.open_folder)
        self.fbtn.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
        self.fbtn.setStyleSheet('''
                                 QPushButton{   
                                             color: #777; font-family:'Arial';
                                             font-weight: bold;
                                             font-size:16px;
                                             border: 2px solid #777;
                                             border-radius: 10px;
                                             min-width: 200px;
                                             padding: 7px;
                                             outline: none;
                                             }'''
                                ) 
        self.viewlabel = QtGui.QLabel("Currents")
        self.viewlabel.setAlignment(QtCore.Qt.AlignCenter)
        self.viewlabel.setStyleSheet('''QLabel{
                                             color: #fff; font-family:'Arial';
                                             font-weight: bold;
                                             font-size:16px;
                                             min-width: 200px;
                                             max-width: 200px;
                                             outline: none;
                                             }'''
                                )
        self.btn = QtGui.QPushButton("Switch to XANES")
        self.btn.clicked.connect(self.switchView)
        self.view = 0
        self.btn.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
        self.btn.setStyleSheet('''
                                 QPushButton{   
                                             color: #777; font-family:'Arial';
                                             font-weight: bold;
                                             font-size:16px;
                                             border: 2px solid #777;
                                             border-radius: 10px;
                                             min-width: 200px;
                                             padding: 7px;
                                             outline: none;
                                             }'''
                                )       
        self.hbl.addWidget(self.fbtn)
        self.hbl.addWidget(self.flabel)
        self.hbl.addWidget(self.viewlabel)
        self.hbl.addWidget(self.btn)
        self.datafilename = None
        
        self.layout.addLayout(self.hbl, 0, 0, 1, 2)
        self.layout.addWidget(self.pw1, 1, 0)
        self.layout.addWidget(self.pw2, 1, 1)
        self.layout.addWidget(self.pw3, 2, 0)
        self.layout.addWidget(self.pw4, 2, 1)
        self.setLayout(self.layout)
        self.app = app
        
        self.counter = 0
        self.energy = []
        self.denergy = []
        self.data_i0 = []
        self.data_i1 = []
        self.data_i2 = []
        self.data_ip = []
        self.mu = []
        self.muf = []
        self.dmu = []
        self.dmuf = []
        self.k = []
        self.kf = []
        self.chi = []
        self.chif = []
        self.r = []
        self.ft_mag = []
        self.rf = []
        self.ft_magf = []
        self.e0i = None
        self.e0if = None
        self.curve1 = self.pw1.plot(self.energy, self.data_i0, pen = "b")
        self.curve2 = self.pw2.plot(self.energy, self.data_i1, pen = "g")
        self.curve3 = self.pw3.plot(self.energy, self.data_i2, pen = "r")
        self.curve4 = self.pw4.plot(self.energy, self.data_ip, pen = "c")
        self.pen_orchid = pg.mkPen(color=(230, 170, 250))
        self.pen_lime = pg.mkPen(color=(190, 250, 0))
        self.text2 = pg.TextItem("", anchor=(0.5, 2))
        self.arrow2 = pg.ArrowItem(angle=-90)
        self.text4 = pg.TextItem("", anchor=(0.5, 2))
        self.arrow4 = pg.ArrowItem(angle=-90)
        
    def signal_received(self, message_buf):
        for message in message_buf:
            if message == "test":
                pass
            elif message == "clear":
                self.counter = 0
                self.energy = []
                self.denergy = []
                self.data_i0 = []
                self.data_i1 = []
                self.data_i2 = []
                self.data_ip = []
                self.mu = []
                self.muf = []
                self.dmu = []
                self.dmuf = []
                self.k = []
                self.chi = []
                self.kf = []
                self.chif = []
                self.r = []
                self.rf = []
                self.ft_mag = []
                self.ft_magf = []
                self.e0i = None
                self.e0if = None
                self.updatePlot() 
            elif (message[-4:] == ".dat") or (message[-4:] == ".nxs"):
                self.flabel.setText(message)
                self.datafilename = message
            else:
                data = [float(v) for v in message.split()] 
                self.energy.append(data[0])
                self.data_i0.append(data[1])
                self.data_i1.append(data[2])
                self.data_i2.append(data[3])
                self.data_ip.append(data[4])
                self.mu.append(np.log(data[1]/data[2]))
                self.muf.append(data[4]/data[1])
        self.updatePlot()            
        if not self.counter%EXAFS_SLOWDOWN_FACTOR:
            self.message_data.emit([self.energy, self.mu, self.muf])
        self.counter += 1        
        self.app.processEvents()

    def switchView(self):
        self.view = (self.view + 1)%3
        if self.view == 0:
            self.viewlabel.setText("Currents")
            self.btn.setText("Switch to XANES")
            self.pw1.setTitle("I0 [counts] / Energy[eV]")
            self.pw2.setTitle("I1 [counts] / Energy[eV]")
            self.pw3.setTitle("I2 [counts] / Energy[eV]")
            self.pw4.setTitle("IP [counts] / Energy[eV]")
            self.pw2.removeItem(self.text2)
            self.pw2.removeItem(self.arrow2)
            self.pw4.removeItem(self.text4)
            self.pw4.removeItem(self.arrow4)
        elif self.view == 1:
            self.viewlabel.setText("XANES")
            self.btn.setText("Switch to EXAFS")
            self.pw1.setTitle("mu trans. / Energy[eV]")
            self.pw2.setTitle("deriv. mu trans. / Energy[eV]")
            self.pw3.setTitle("mu fluo. / Energy[eV]")
            self.pw4.setTitle("deriv. mu fluo. / Energy[eV]")
        elif self.view == 2:
            self.viewlabel.setText("EXAFS")
            self.btn.setText("Switch to Currents")
            self.pw1.setTitle(u"\u03C7" + "(k)*k^2 trans. / k[" + u"\u212B" + "^-1]")
            self.pw2.setTitle("| FT(" + u"\u03C7" + "(k)*k^2 trans." + ") | / R[" + u"\u212B" + "]")
            self.pw3.setTitle(u"\u03C7" + "(k)*k^2 fluo. / k[" + u"\u212B" + "^-1]")
            self.pw4.setTitle("| FT(" + u"\u03C7" + "(k)*k^2 fluo." + ") | / R[" + u"\u212B" + "]")
            self.pw2.removeItem(self.text2)
            self.pw2.removeItem(self.arrow2)
            self.pw4.removeItem(self.text4)
            self.pw4.removeItem(self.arrow4)
            
        #https://github.com/pyqtgraph/pyqtgraph/issues/821    
        self.pw1.getAxis('left').textWidth = 0
        self.pw1.getAxis('left')._updateWidth()
        self.pw2.getAxis('left').textWidth = 0
        self.pw2.getAxis('left')._updateWidth()
        self.pw3.getAxis('left').textWidth = 0
        self.pw3.getAxis('left')._updateWidth()
        self.pw4.getAxis('left').textWidth = 0
        self.pw4.getAxis('left')._updateWidth()

        self.pw1.enableAutoRange()
        self.pw2.enableAutoRange()
        self.pw3.enableAutoRange()
        self.pw4.enableAutoRange()
        self.updatePlot()
            
    def updatePlot(self):
        if self.view == 0:
            self.curve1.setData(self.energy, self.data_i0)
            self.curve1.setPen("b")
            self.curve2.setData(self.energy, self.data_i1)
            self.curve2.setPen("g")
            self.curve3.setData(self.energy, self.data_i2)
            self.curve3.setPen("r")
            self.curve4.setData(self.energy, self.data_ip)
            self.curve4.setPen("c")   
        elif self.view == 1:
            self.curve1.setData(self.energy, self.mu)
            self.curve1.setPen(self.pen_lime)
            self.curve2.setData(self.denergy, self.dmu)
            self.curve2.setPen(self.pen_lime)
            self.pw2.removeItem(self.text2)
            self.pw2.removeItem(self.arrow2)
            if self.e0i is not None:
                self.text2.setText("%.2f"%self.denergy[self.e0i]) 
                self.text2.setPos(self.denergy[self.e0i], self.dmu[self.e0i])
                self.arrow2.setPos(self.denergy[self.e0i], self.dmu[self.e0i])
                self.pw2.addItem(self.text2)
                self.pw2.addItem(self.arrow2)
            self.pw4.removeItem(self.text4)
            self.pw4.removeItem(self.arrow4)
            self.curve3.setData(self.energy, self.muf)
            self.curve3.setPen(self.pen_orchid)
            self.curve4.setData(self.denergy, self.dmuf)
            self.curve4.setPen(self.pen_orchid)
            if self.e0if is not None:
                self.text4.setText("%.2f"%self.denergy[self.e0if]) 
                self.text4.setPos(self.denergy[self.e0if], self.dmuf[self.e0if])
                self.arrow4.setPos(self.denergy[self.e0if], self.dmuf[self.e0if])
                self.pw4.addItem(self.text4)
                self.pw4.addItem(self.arrow4)
        elif self.view == 2:
            self.curve1.setData(self.k, self.chi)
            self.curve1.setPen(self.pen_lime)
            self.curve2.setData(self.r, self.ft_mag)
            self.curve2.setPen(self.pen_lime)
            self.curve3.setData(self.kf, self.chif)
            self.curve3.setPen(self.pen_orchid)
            self.curve4.setData(self.rf, self.ft_magf)
            self.curve4.setPen(self.pen_orchid)        
    
    def update_exafs(self, data_list):
        self.e0i, self.dmu = data_list[0], data_list[1][:]
        self.k, self.chi = data_list[2][:], data_list[3][:]
        self.r, self.ft_mag = data_list[4][:], data_list[5][:]
        self.e0if, self.dmuf  =  data_list[6], data_list[7][:]
        self.kf, self.chif = data_list[8][:], data_list[9][:]
        self.rf, self.ft_magf = data_list[10][:], data_list[11][:]
        self.denergy = data_list[12][:]
        self.updatePlot()
    
    def open_folder(self):
        if self.datafilename:
            os.system('xdg-open "%s"' %os.path.dirname(self.datafilename))
                
    def closeEvent(self, event):
        self.zeromq_listener.running = False
        self.zeromq_listener.finish()
        self.thread.quit()
        self.thread.wait()    
        self.thread2.quit()
        self.thread2.wait()  
        self.app.processEvents()
        
            
if __name__ == '__main__':
    app = QtGui.QApplication([])
    mw = MonitorWidget(app)
    mw.setStyleSheet("background-color: #000")
    mw.setWindowTitle("Data monitor")
    mw.show()
    sys.exit(app.exec_())
