"""
@author: Ruidy Nemausat
"""

from EXAFS_Monitor.monitor_gui import MonitorWidget
import sys
from PyQt5.QtWidgets import QApplication, QWidget
from main_gui import MainGui
from qexafs import QexafsGui

from functools import partial


class AddScan(QWidget, QexafsGui):
    """
    Widget used to create new scans
    """

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.save_scans)
        self.pushButton_2.clicked.connect(self.clear)

    def save_scans(self):
        """
        Create list of scan
        """
        line = [
            f"{self.tableWidget.verticalHeaderItem(i).text()}: {self.tableWidget.item(i, 0).text()}" for i in range(11)]
        self.listWidget.addItem(str(self.listWidget.count()+1)+", ".join(line))

    def clear(self):
        for line in range(11):
            self.tableWidget.item(line, 0).setText('')


class XafsManager(QWidget, MainGui):
    """
    Graphical-User Interface for P65 beamline
    """

    def __init__(self):
        """
        constructor: initializes GUI layout from MainGui class
        """
        super().__init__()
        self.setupUi(self)

        self.pushButton.clicked.connect(self.add_scan)

    def add_scan(self):
        self.add = AddScan()
        self.add.show()

        # self.connect(
        #     self.loadLast,
        #     SIGNAL("clicked()"),
        #     partial(self.readLast)
        # )

        # self.connect(
        #     self.add2list,
        #     SIGNAL("clicked()"),
        #     partial(self.make_dict, scanListe)
        # )

        # self.connect(
        #     self.start,
        #     SIGNAL("clicked()"),
        #     partial(self.startScans)
        # )

        # self.connect(
        #     self.clearList,
        #     SIGNAL("clicked()"),
        #     partial(self.clearScans, scanListe)
        # )
        #
#     def make_dict(self, scanListe):
#         """
#         Defines a single scan and returns the parameter as a dictionary object
#         """
#         edge_n = str(self.edge_name.text())
#         if str(edge_n) == "":
#             showMessageBox(self, "Edge Name")
#         # dsPar = str(self.ds_param.text())
#         # """if str(dsPar) == "":
#             # 	EXAFS_GUI_common.showMessageBox(self,"DS parameter")"""
#         edge_e = str(self.edge_energy.text())
#         if str(edge_e) == "":
#             showMessageBox(self, "Edge energy")
#         sam_p = str(self.sam_pos.text())
#         if str(sam_p) == "":
#             showMessageBox(self, "Sample Position")
#         sam_n = str(self.sam_name.text())
#         if str(sam_n) == "":
#             showMessageBox(self, "Sample Name")
#         sam_r = str(self.sam_rep.text())
#         if str(sam_r) == "":
#             showMessageBox(self, "Number of repetitions")
#         motor_n = str(self.motor_number.text())
#         if str(motor_n) == "":
#             showMessageBox(self, "Motor number")
#         # there is always a value, so no check
#         keith1 = str(self.keith_1.value())
#         keith2 = str(self.keith_2.value())
#         keith3 = str(self.keith_3.value())
#         keith4 = str(self.keith_4.value())
#         cont_s = str(self.cont_start.text())
#         if str(cont_s) == "":
#             showMessageBox(self, "Energy start")
#         if float(cont_s) < 0:  # Correct automatically if users insert a negative value
#             cont_s = str(float(cont_s) * -1)
#             print(cont_s)
#         cont_en = str(self.cont_stop.text())
#         if str(cont_en) == "":
#             showMessageBox(self, "Energy scan end")
#         cont_t = str(self.cont_tot_time.text())
#         if str(cont_t) == "":
#             showMessageBox(self, "Time per scan")
#         tpp = str(self.timepp.text())
#         if str(tpp) == "":
#             showMessageBox(self, "Time per point")
#         und_o = str(self.und_off.text())
#         if str(und_o) == "":
#             showMessageBox(self, "Undulator offset")
#         data_d = str(self.data_dir.text())
#         if str(data_d) == "":
#             showMessageBox(self, "Data directory")
#         type_t = self.type_trans.isChecked()
#         type_p = self.type_pips.isChecked()
#         type_x = self.type_Xia.isChecked()
#         which_d = str(self.StorageChooser.currentText())
#         ds_1 = self.do_something_1.isChecked()
#         ds_2 = self.do_something_2.isChecked()

# # Write the input into a dictionary
#         scan_spec = {
#             "edge_n": edge_n,
#             "dsPar": dsPar,
#             "edge_e": edge_e,
#             "sam_p": sam_p,
#             "sam_n": sam_n,
#             "sam_r": sam_r,
#             "keith1": keith1,
#             "keith2": keith2,
#             "keith3": keith3,
#             "keith4": keith4,
#             "motor_n": motor_n,
#             "cont_s": cont_s,
#             "cont_en": cont_en,
#             "cont_t": cont_t,
#             "tpp": tpp,
#             "und_o": und_o,
#             "data_d": data_d,
#             "type_t": type_t,
#             "type_p": type_p,
#             "type_x": type_x,
#             "which_d": which_d,
#             "ds_1": ds_1,
#             "ds_2": ds_2
#         }
#         with open(path + '/last_cont_scan.json', 'w') as f3:
#             # Use to restore last scan's settings
#             json.dump(scan_spec, f3, indent=2)
#         scanListe.append(scan_spec)
#         print("Make my scan...")
#         if os.path.isfile(path + "/ListOfScans.json"):
#             os.remove(path + "/ListOfScans.json")
#         with open(path + '/ListOfScans.json', 'a') as f1:
#             json.dump(scanListe, f1, indent=2)
#         print(scanListe)

#         return scanListe

#     def showMessageBox(self):
#         QMessageBox.information(
#             self, "Problem!!!", "Clicked")


def main():
    """
    Displays a XafsManager window
    """
    app = QApplication(sys.argv)
    x = XafsManager()
    x.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
