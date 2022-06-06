from src.InputManager import InputManager
from re import T
import subprocess
import sys
from sys import platform
from notifypy import Notify
import yaml
import time
from random import randrange
from time import sleep
from PIL import Image
import numpy
import cv2
def getNowMs():
    return time.time() * 1000

if platform == "windows":
    import win32gui
    import win32ui
    import win32api
    import win32con
    from ctypes import windll
    import pyautogui



print("Loading user preferences from preferences.yml")
UserConfig = yaml.safe_load(open('preferences.yml'))
if UserConfig:
    print("Loaded user preferences successfully.")
else:
    print("Could not load user preferences.")
    sys.exit()
# print(UserConfig)

# Constants
ScriptDebugEnabled = False
StatsLocation = UserConfig["settings"]["player"]["status"]["location"]
StatsCropbox = UserConfig["settings"]["player"]["status"]["cropbox"]
HealthPixelColor = (241, 97, 97)
ManaPixelColor = (83, 80, 218)
BarsWidth = 100
BarsHeight = 23
BarsRange = BarsWidth -1
BarsInitialStep = 5
HpBarMiddle = 5
MpBarMiddle = 17  

ScriptStatus = False

def Execute(cmd):
    output, _ = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()
    return output.decode("utf8")

MirrorWindowTitle = "Windowed Projector (Source) - Game Capture"
MirrorWindowHandle = UserConfig["settings"]["game"]["handle"]
if platform == "windows":
    mirrorWindow = pyautogui.getWindowsWithTitle(MirrorWindowTitle)
    if(mirrorWindow):
        MirrorWindowHandle = mirrorWindow[0]._hWnd
elif platform == "linux":
    MirrorWindowHandle = 999

UserConfig["settings"]["mirror"]["handle"] = MirrorWindowHandle

    
TibiaWindowTitle = "Tibia - "
TibiaWindowHandle = UserConfig["settings"]["game"]["handle"]
if platform == "windows":
    tibiaWindow = pyautogui.getWindowsWithTitle(TibiaWindowTitle)
    if(tibiaWindow):
        TibiaWindowHandle = tibiaWindow[0]._hWnd    
        
elif platform == "linux":
    savedHandle = UserConfig["settings"]["game"]["handle"]
    savedExists = Execute(["xdotool", "getwindowname", savedHandle])

    if(savedExists):
        print("Loaded Tibia Client handle from previous session.")
        TibiaWindowHandle = savedHandle
    else:
        handle = Execute(["xdotool", "search", "--name", "Tibia -"])
        print("Tibia Handle Found")
        print(handle.split("\n")[0])

        # Remove trailing line breaks from search result
        TibiaWindowHandle = handle.split("\n")[0]

        if not TibiaWindowHandle:
            print("You have to be logged in a character for Tibia Client to be properly detected.")
            print("Open TibiaFlask again.")
            print("Exiting TibiaFlask...")
            sys.exit()

UserConfig["settings"]["game"]["handle"] = TibiaWindowHandle


# Rule Constants
HealingSpellExhaustTimer = getNowMs()
HealingSpellExhaustTime = 100
PotionExhaustTimer = getNowMs()
PotionExhaustTime = 100

# Stage Constants
HealthPotionStage1Percent = UserConfig["stages"]["potions"]["health"]["one"]["percentage"]
HealthPotionStage1Hotkey  = UserConfig["stages"]["potions"]["health"]["one"]["hotkey"]

HealthPotionStage2Percent = UserConfig["stages"]["potions"]["health"]["two"]["percentage"]
HealthPotionStage2Hotkey  = UserConfig["stages"]["potions"]["health"]["two"]["hotkey"]

ManaPotionStage1Percent = UserConfig["stages"]["potions"]["mana"]["one"]["percentage"]
ManaPotionStage1Hotkey = UserConfig["stages"]["potions"]["mana"]["one"]["hotkey"]

HealingSpellStage1Percent = UserConfig["stages"]["spells"]["healing"]["one"]["percentage"]
HealingSpellStage1Hotkey  = UserConfig["stages"]["spells"]["healing"]["one"]["hotkey"]

UturaTime = 61000
UturaTimer = getNowMs()
UturaHotkey = UserConfig["stages"]["spells"]["support"]["utura"]["hotkey"]

FoodTime = UserConfig["stages"]["support"]["food"]["time-repeat-ms"]
FoodTimer = getNowMs()
FoodHotkey = UserConfig["stages"]["support"]["food"]["hotkey"]

with open('preferences.yml', 'w') as file:
    yaml.dump(UserConfig, file);

    
if(platform == 'windows'):
    def GrabImage(hwnd = pyautogui.getActiveWindow()):
        # Change the line below depending on whether you want the whole window
        # or just the client area. 
        left, top, right, bot = win32gui.GetClientRect(hwnd)
        # left, top, right, bot = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bot - top

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

        saveDC.SelectObject(saveBitMap)

        # Change the line below depending on whether you want the whole window
        # or just the client area. 
        #result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 1)
        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        im = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        #   print('Debug: Image Grab.')
        return im

elif(platform == 'linux'):
    def GrabImage():
        # print("Grabbing Image")
        file = 'snapshots/tmp_scrot.png'
        Execute(["rm", "-rf", file])
        Execute(["scrot", "-u", file])
        im = Image.open(file)
        return im


def LocateImage(mainImage, compareImage, precision=0.8):
    img_rgb = numpy.array(mainImage)
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
    template = cv2.imread(compareImage, 0)

    res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
    min_val, LocatedPrecision, min_loc, Position = cv2.minMaxLoc(res)
    print("LocatedPrecision")
    print(LocatedPrecision)
    if LocatedPrecision > precision:
        return Position[0], Position[1]
    return 0, 0

def PixelMatchRGB(image, coords, expectedRgb):
    # print("Getting pixel color")
    rgb = image.getpixel((coords[0], coords[1]))
    if rgb == expectedRgb:
        return True
    else:
        return False

def ScanStats(statsImage):
    hpPercent = 0
    mpPercent = 0

    for i in range(BarsInitialStep, BarsRange, 1):
        if PixelMatchRGB(statsImage, (i, HpBarMiddle), HealthPixelColor):
            hpPercent = i + 1
        if PixelMatchRGB(statsImage, (i, MpBarMiddle), ManaPixelColor):
            mpPercent = i + 1
            
    return (hpPercent, mpPercent)

def TakeMirrorImage(MirrorHwnd):
    # print("Debug: Taking Mirror Image")
    if(platform == "windows"):
        img = GrabImage(MirrorHwnd)
    elif(platform == "linux"):
        img = GrabImage()

    return img
    
def CheckStatsRoutine():
    img = TakeMirrorImage(MirrorWindowHandle)
    crop = img.crop(box=StatsCropbox)
    statsImg = crop.resize((BarsWidth, BarsHeight))
    
    return ScanStats(statsImg)

def GetActiveHwnd():
    if platform == "linux":
        window = Execute["xdotool", "getactivewindow"].split("\n")[0]
        if window:
            return window
        else:
            return None

def doConfig():
    print('HUD Configuration Initialized')

    
    if platform == "linux":
        MirrorWindowHandle = 999

    if(MirrorWindowHandle != 0):        
        gameImage = TakeMirrorImage(MirrorWindowHandle)
        located = LocateImage(gameImage, "./health.png")
        gameImage.save('testimg.png')

        if(located[0] != 0 and located[1] != 0):
            StatsLocation[0] = located[0]
            StatsLocation[1] = located[1]
            UserConfig["settings"]["player"]["status"]["location"] = StatsLocation
            
            cropBox = top, left, right, bottom = StatsLocation[0] +14, StatsLocation[1], StatsLocation[0] + 5 + 100, StatsLocation[1] + 23
            StatsCropbox[0] = cropBox[0]
            StatsCropbox[1] = cropBox[1]
            StatsCropbox[2] = cropBox[2]
            StatsCropbox[3] = cropBox[3]
            UserConfig["settings"]["player"]["status"]["cropbox"] = StatsCropbox
        
            print("Health and Mana status were located successfully.")
        else:
            StatsLocation[0] = 0
            StatsLocation[1] = 0
            print("Health and Mana status could not be located.")
    else:   
        print('No mirror window handle could be found.')
    
    print("Debug: MirrorWindowHandle")
    print(str(MirrorWindowHandle) + "\n")
    print("Debug: TibiaWindowHandle")
    print(str(TibiaWindowHandle) + "\n")
    print("Debug: StatsLocation")
    print(str(StatsLocation) + "\n")
    return
            
def toggleBool(Status):
    if(Status):
        Status = False
        print("Disabling")
    else:
        Status = True
        print("Enabling")
        
    sleep(0.200)
    return Status
  
def isWinActive(targetHwnd):
    if platform == "windows":
        currentWindow = pyautogui.getActiveWindow()
        if(currentWindow):
            if(currentWindow._hWnd == targetHwnd):
                return True
            else:
                return False
        else:
            return False
    elif platform == "linux":
        currentHwnd = Execute(["xdotool", "getactivewindow"]).split("\n")[0]
        
        if(currentHwnd):
            if(currentHwnd == targetHwnd):
                return True
            else:
                return False
        else:
            return False

def isExhausted(exhaustTimer, exhaustTime):
    diff = getNowMs() - exhaustTimer
    if diff >= exhaustTime:
        return False
    else:
        return True
    
def ReloadUserPreferences():
    print("Reloading user config...")    
    with open('preferences.yml', 'w') as file:
            yaml.dump(UserConfig, file);
    print("Reloaded and updated user preferences.")

def ExitFlask():
    print("Saving User Preferences...")
    with open('preferences.yml', 'w') as file:
        yaml.dump(UserConfig, file);
    
    print("Exiting TibiaFlask...")
    sys.exit()

def NotifyUserMessage(msg):
    notification = Notify()
    notification.title = "TibiaFlask"
    notification.message = msg
    notification.send()

while 1:
    try:
        if InputManager.IsPressed("ctrl+shift+1"):
            ScriptStatus = toggleBool(ScriptStatus)
            # NotifyUserMessage("TibiaFlask Status: "  + str(ScriptStatus))
            sleep(0.2)
            
        if InputManager.IsPressed("ctrl+shift+2"):
            doConfig()
            sleep(0.2)
            
        if InputManager.IsPressed("shift+end"):
            # NotifyUserMessage("Ending TibiaFlask...")
            ExitFlask()
            
        if(ScriptStatus):
            if isWinActive(TibiaWindowHandle):
                if ScriptDebugEnabled:
                    now = getNowMs()
                    print("Debug: Health and Mana Stats")
                    print(str(stats) + "\n")
                
                stats = CheckStatsRoutine()
                currentHealthPercent = stats[0]
                currentManaPercent = stats[1]
                
                # Support Spells & Food -> non-danger situation, not-exhausted (probably not in combat)
                if((not isExhausted(HealingSpellExhaustTimer, HealingSpellExhaustTime)) and (not isExhausted(PotionExhaustTimer, PotionExhaustTime))):
                    if(currentHealthPercent > 70 and currentManaPercent > 20):
                        if(not isExhausted(UturaTimer, UturaTime)):
                            print("Casting Utura.")
                            # Perform Action
                            InputManager.SendKeystroke(UturaHotkey)
                            sleep((randrange(45,70) / 1000))
                            InputManager.SendKeystroke(UturaHotkey)
                            
                            # Reset Timer
                            UturaTimer = getNowMs()
                            
                        if(not isExhausted(FoodTimer, FoodTime) and isExhausted(UturaTimer, UturaTime)):
                            print("Eating Food.")
                            # Perform Action
                            InputManager.SendKeystroke(FoodHotkey)
                            sleep((randrange(45,70) / 1000))
                            InputManager.SendKeystroke(FoodHotkey)

                            # Reset Timer
                            FoodTimer = getNowMs()
                
                # Healing Spell -> Has mana, should call before potion
                if(not isExhausted(HealingSpellExhaustTimer, HealingSpellExhaustTime)):
                    if(currentHealthPercent < HealingSpellStage1Percent and currentManaPercent > 5):
                        # Perform Action
                        InputManager.SendKeystroke(HealingSpellStage1Hotkey)
                        sleep((randrange(45,70) / 1000))
                        InputManager.SendKeystroke(HealingSpellStage1Hotkey)
                        
                        # Reset Timer
                        HealingSpellExhaustTimer = getNowMs()
                
                # Potions
                if(not isExhausted(PotionExhaustTimer, PotionExhaustTime)):
                    if(currentHealthPercent < HealthPotionStage2Percent):
                        # Perform Action                    
                        InputManager.SendKeystroke(HealthPotionStage2Hotkey)
                        sleep((randrange(45,70) / 1000))
                        InputManager.SendKeystroke(HealthPotionStage2Hotkey)
                        
                        # Reset Timer
                        PotionExhaustTimer = getNowMs()
                        
                    elif(currentHealthPercent < HealthPotionStage1Percent):
                        # Perform Action                                       
                        InputManager.SendKeystroke(HealthPotionStage1Hotkey)
                        sleep((randrange(45,70) / 1000))
                        InputManager.SendKeystroke(HealthPotionStage1Hotkey)
                        
                        # Reset Timer
                        PotionExhaustTimer = getNowMs()
                    
                    elif(currentManaPercent < ManaPotionStage1Percent):
                        # Perform Action     
                        InputManager.SendKeystroke(ManaPotionStage1Hotkey)
                        sleep((randrange(45,70) / 1000))
                        InputManager.SendKeystroke(ManaPotionStage1Hotkey)

                        # Reset Timer
                        PotionExhaustTimer = getNowMs()
                        
                if ScriptDebugEnabled:
                    diff = getNowMs() - now                
                    print("Debug: Status reading took ms: \n" + str(diff))        
            sleep(0.05)
    except KeyboardInterrupt:
        ExitFlask()
        
