from PyQt4.QtGui import QSystemTrayIcon

icon = QSystemTrayIcon()
#icon.setVisible(True)
icon.showMessage("Message", "Message")
import time
time.sleep(2)
