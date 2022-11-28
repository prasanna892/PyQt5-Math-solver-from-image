# Importing required module
from time import sleep
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys, json
from pathlib import Path
import keyboard, re, os
import pytesseract as pt
from PIL import Image


# Creating OCR math solver
class OCR_MathSolver():
    def __init__(self, OCR_path):
        # Setting path of tesseract executable
        pt.pytesseract.tesseract_cmd = OCR_path

    # Converting image to valid math expression
    def imageTOtext(self, image):
        text = pt.image_to_string(Image.open(image), lang ='eng', config='--psm 7') # Getting text from image

        # Converting text to valid math expression
        table = str.maketrans('{}[]xX', '()()**')
        valid_expression = re.sub('[^0-9()/*\-+]', '', text.translate(table))

        return valid_expression
        
    # Solving math expression
    def math_solver(self, image):
        expression = self.imageTOtext(image)

        try:
            result = eval(expression)
        except:
            result = 'Error'

        return expression, result
        

# Creating solver widget
class SolverWidget(QWidget):
    def __init__(self, OCR_solver, parent = None):
        super(QWidget, self).__init__(parent = None)

        # Setting window look
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.90)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Setting window geomentry and keys
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.setHotkey()
        self.key_hook = keyboard.hook(self.CustomkeyboardEvent)

        # Creating required labels
        self.crop = QLabel(self)
        self.crop.setAlignment(Qt.AlignTop)
        self.crop.setGeometry(0, 0, self.width(), self.height())
        self.crop.setStyleSheet("background-color: rgba(0, 0, 0, 0); border: 3px solid orange")

        self.result = QLabel(self)
        self.result.setGeometry(0, 0, 355, 199)
        self.result.setAlignment(Qt.AlignCenter)
        self.result.setFont(QFont("Consolas", 16, 5, True))
        self.result.setStyleSheet("background-color: rgba(0, 0, 255, 150); border: 1px solid black; color: rgb(255, 255, 0)")
        self.result_hidden = False
        self.result.setHidden(True)

        # Creating required timers
        # For update screen
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(10)
        # For lock screen animation
        self.lock_ani_timer = QTimer()
        self.lock_ani_timer.timeout.connect(self.lock_effects)
        self.lock_ani_timer.start(150)

        # creating required initial variable
        # Storing monitor info
        self.monitor = self.screen()
        self.monitor_geometry = self.monitor.geometry()

        # For check screen change
        self.cursor_old_pos = QCursor.pos()
        self.if_screen_changed = True
        
        # For lock screen animation
        self.lock_ani_flash = False

        # For selecting area
        self.grabed_rect1 = [0,0]
        self.grabed_rect2 = [self.monitor_geometry.width(), self.monitor_geometry.height()]
        self.ctrl_pressed = False
        self.crop_started = False

        # For locking monitor
        self.locked_monitor = self.monitor
        self.locked_area = None

        # For OCR to solve problem
        self.OCR_mathSolver = OCR_solver
        self.question = None
        self.solved_answer = None

    # Checking for screen changes
    def if_screen_change(self, oldPos=None, newPos=None):
        self.cursor_new_pos = QCursor.pos()
        oldScreen = QApplication.screenAt(oldPos if oldPos else self.cursor_old_pos)
        newScreen = QApplication.screenAt(newPos if newPos else self.cursor_new_pos)
    
        if not oldScreen == newScreen:
            self.if_screen_changed = True
            self.cursor_old_pos = self.cursor_new_pos
            return newScreen
        return None

    # Check which screen is selected and changing some value according to selected monitor
    def check_screen_at(self):
        self.cursor_new_pos = QCursor.pos()
        newScreen = self.if_screen_change()
        if newScreen:
            newScreen_x, newScreen_y, newScreen_w, newScreen_h = newScreen.geometry().getRect()
                
            self.crop.setHidden(False)
            self.crop.setStyleSheet("border: 3px solid orange")

            self.move(newScreen_x, newScreen_y)
            self.setFixedSize(newScreen_w, newScreen_h)

            self.crop.setGeometry(0, 0, newScreen_w, newScreen_h)

            self.monitor = newScreen
            self.monitor_geometry = self.monitor.geometry()

            self.grabed_rect1 = [0, 0]
            self.grabed_rect2 = [self.monitor_geometry.width(), self.monitor_geometry.height()]

    # Drawing crop area
    def draw_croping_area(self):
        if not self.ctrl_pressed:
            self.ctrl_pressed = True
            self.grabed_rect1 = [abs(QCursor.pos().x()-self.monitor_geometry.x()), abs(QCursor.pos().y()-self.monitor_geometry.y())]
        
        self.grabed_rect2 = [abs(QCursor.pos().x()-self.monitor_geometry.x()), abs(QCursor.pos().y()-self.monitor_geometry.y())]
        
        x_pointS, y_pointS = self.grabed_rect1
        x_pointE, y_pointE = self.grabed_rect2

        width = abs(x_pointS-x_pointE)
        height = abs(y_pointS-y_pointE)
        self.crop.setGeometry(x_pointS, y_pointS, width, height)

    # Setting lock effect
    def lock_effects(self):
        if self.lock_ani_flash:
            if self.lock_ani_flash%2:
                self.crop.setStyleSheet("border: 3px solid red")
            else:
                self.crop.setStyleSheet("border: 3px solid green")
            self.lock_ani_flash += 1
            
            if self.lock_ani_flash==8:
                self.lock_ani_flash = False
                self.crop.setHidden(True)

    # Locking selected area
    def lock_selected_area(self):
        self.crop.setHidden(False)
        self.lock_ani_flash = True
        self.locked_monitor = self.monitor
        self.locked_area = (self.grabed_rect1[0], self.grabed_rect1[1], abs(self.grabed_rect1[0]-self.grabed_rect2[0]), abs(self.grabed_rect1[1]-self.grabed_rect2[1])) 

    # Show or hide cropped area
    def show_crop_area(self, bool):
        self.crop_started = self.if_screen_changed = False
        self.crop.setHidden(not bool) # Setting crop label hidden or show
        self.crop.setStyleSheet("border: 3px solid blue") # Changing crop label boarder
        if self.locked_area and self.locked_monitor == self.monitor:
            self.crop.setGeometry(*self.locked_area) # Setting crop label geomentry

    # Grabing screenshot and try to find answer
    def find_answer(self):
        if self.locked_area:
            screenshot = self.locked_monitor.grabWindow(0, *self.locked_area) # Screenshot on selected area
            screenshot.save('temp.jpg', 'jpg') # Saving screenshot
            self.question, self.solved_answer = self.OCR_mathSolver.math_solver('temp.jpg') # Calling math solver method
            os.remove('temp.jpg') # Permanently delete saved screenshot

            self.show_result()

    # To display result at top right corner of selected monitor
    def show_result(self):
        self.result_hidden = True
        self.result.setHidden(False) # unhiden result label
        self.result.setText(str(self.question)+'\n=>'+str(self.solved_answer)) # setting answer to result label

    # Answer auto-typer
    def write_result(self):
        keyboard.write(str(self.solved_answer))
        
    # Function to hide some property after t milli-sec
    def hide_object(self, trigger, object_to_hide, ms=500):
        if trigger:
            trigger += 1
            if trigger >= ms:
                trigger = False
                object_to_hide.setHidden(True) # Hide given object
        return trigger

    # Setting hotkeys
    def setHotkey(self):
        keyboard.add_hotkey('alt + shift + l', self.lock_selected_area) # To lock croped area
        keyboard.add_hotkey('alt + shift + s', self.show_crop_area, args=(True,)) # To show croped area
        keyboard.add_hotkey('alt + shift + h', self.show_crop_area, args=(False,)) # To hide croped area
        keyboard.add_hotkey('alt + shift + o', self.find_answer) # To find math answer
        keyboard.add_hotkey('alt + shift + a', self.show_result) # To display answer in screen
        keyboard.add_hotkey('alt + shift + r', self.write_result) # To auto-type answer

    # Creating Custom key event
    def CustomkeyboardEvent(self, event):
        if event.event_type == 'down':
            if event.name == 'ctrl':
                self.crop.setStyleSheet("border: 3px solid green")
                self.draw_croping_area()
                self.crop.setHidden(False)

        if event.event_type == 'up':
            if event.name == 'ctrl':
                self.crop_started = True
                self.ctrl_pressed = False

    # Updaing solver widget screen
    def update(self):
        self.check_screen_at()
        self.result_hidden = self.hide_object(self.result_hidden, self.result)
        self.if_screen_changed = self.hide_object(self.if_screen_changed, self.crop)
        self.crop_started = self.hide_object(self.crop_started, self.crop)

    # Setting what to do when close
    def finish(self):
        keyboard.unhook(self.key_hook)
        keyboard.unhook_all_hotkeys()


# Creating system tray icon
class SolverSystemTray(QSystemTrayIcon):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        
        # Setting icon
        icon = QIcon('./assets/icon.ico')
        self.setIcon(icon)
        self.setVisible(True)
        self.setToolTip("Help you to solve math problems") # Setting tool tip

        # Start-up method calling
        self.menuCreation(parent)
        
        self.solver_open = False
        self.text_box_autoclose = False

        # Calling OCR_MathSolver() class
        self.OCR_mathSolver = OCR_MathSolver(self.check_if_ocr_exists())

    # Checking OCR path is valid
    def check_if_ocr_exists(self):
        # Opening JSON file
        with open('./assets/config.json', 'r') as f:
            data = json.load(f)
        
        if Path(data['ocr_exe_path']).is_file() and data['ocr_exe_path'].endswith('.exe'):
            self.show_notification('Start-Up message', 'SimpleMathSolver.exe successfully launched on system tray, click to start Solver')
            return data['ocr_exe_path']
        else:
            return self.show_input_messagebox()
        
    # Input messagebox to get OCR path
    def show_input_messagebox(self, defult_text='Example: F:\\ocr\\tesseract.exe'):
        self.text_box = QInputDialog(None)
        self.text_box.setFont(QFont("Consolas", 12, 5, True))
        self.text_box.setWindowIcon(self.icon())
        self.text_box.setWindowTitle('OCR exe path')
        self.text_box.setLabelText('Enter tesseract OCR exe file path:')
        self.text_box.setTextValue(defult_text)
        self.text_box.textValueChanged.connect(self.autoClose)

        if self.text_box.exec() or self.text_box_autoclose:
            text = self.text_box.textValue()
            if Path(text).is_file() and text.endswith('.exe'):
                self.show_notification('Start-Up message', 'SimpleMathSolver.exe successfully launched on system tray, click to start Solver')
                return text
            else:
                return self.show_input_messagebox('Enter valid OCR path')
        elif not self.text_box_autoclose:
            sys.exit()
            
    # If valid path is entered then auto close input messagebox
    def autoClose(self, text):
        if Path(text).is_file() and text.endswith('.exe'):
            # Writing path to json file
            with open('./assets/config.json', 'w') as f:
                json.dump({"ocr_exe_path": text}, f, indent=4)
            self.text_box_autoclose = self.text_box.close()

    # Showing notification
    def show_notification(self, title:str, msg:str, msec=1):
        self.showMessage(title, msg, msecs=msec)
        self.messageClicked.connect(self.triggerSolver)

    # Creating menu
    def menuCreation(self, parent):
        self.menu = QMenu(parent) # Creating context menu

        # Adding 'Start solver' option
        self.show_crop_area = self.menu.addAction("Start solver")
        self.show_crop_area.setIcon(QIcon('./assets/StartSearch.png'))
        self.show_crop_area.triggered.connect(self.triggerSolver)

        # Adding 'Exit' option
        self.exit_action = self.menu.addAction("Exit")
        self.exit_action.setIcon(QIcon('./assets/close.png'))
        self.exit_action.triggered.connect(self.finish)

        self.setContextMenu(self.menu) # Setting context menu

    # Starting or closing solver widget
    def triggerSolver(self):
        if not self.solver_open:
            self.solver_widget = SolverWidget(self.OCR_mathSolver)
            self.solver_widget.show()
            self.show_crop_area.setIcon(QIcon('./assets/StopSearch.png'))
            self.show_crop_area.setText("Close solver")
        else:
            self.solver_widget.finish()
            self.solver_widget.close()
            self.show_crop_area.setIcon(QIcon('./assets/StartSearch.png'))
            self.show_crop_area.setText("Start solver")

        self.solver_open = not self.solver_open

    # To close
    def finish(self):
        QCoreApplication.instance().quit()  # Quit all window


# Creating application
def main():
    app = QApplication(sys.argv)
    solver_tray = SolverSystemTray()
    solver_tray.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()