import sys
import yaml

import time
def getNowMs():
    return time.time() * 1000

from random import randrange
from pstats import Stats
from pydoc import locate
from time import sleep
import win32gui
import win32ui
import win32api
import win32con
from ctypes import windll
from PIL import Image
import pyautogui
import keyboard
import numpy
import cv2

UserConfig = yaml.safe_load(open('preferences.yml'))
print("Loading User Config")
print(UserConfig)

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



MirrorWindowTitle = "Windowed Projector (Source) - Game Capture"
MirrorWindowHandle = UserConfig["settings"]["game"]["handle"]
mirrorWindow = pyautogui.getWindowsWithTitle(MirrorWindowTitle)
if(mirrorWindow):
    MirrorWindowHandle = mirrorWindow[0]._hWnd
    UserConfig["settings"]["mirror"]["handle"] = MirrorWindowHandle
    
    
TibiaWindowTitle = "Tibia - "
TibiaWindowHandle = UserConfig["settings"]["game"]["handle"]
tibiaWindow = pyautogui.getWindowsWithTitle(TibiaWindowTitle)
if(tibiaWindow):
    TibiaWindowHandle = tibiaWindow[0]._hWnd    
    UserConfig["settings"]["game"]["handle"] = TibiaWindowHandle

# Rule Constants
HealingSpellExhaustTimer = getNowMs()
HealingSpellExhaustTime = 1000
PotionExhaustTimer = getNowMs()
PotionExhaustTime = 1000

# Stage Constants
HealthPotionStage1Percent = 60
HealthPotionStage1Hotkey  = win32con.VK_F1

HealthPotionStage2Percent = 20
HealthPotionStage2Hotkey  = win32con.VK_F2

ManaPotionStage1Percent = 85
ManaPotionStage1Hotkey = win32con.VK_F3

HealingSpellStage1Percent = 95
HealingSpellStage1Hotkey  = win32con.VK_F4

with open('preferences.yml', 'w') as file:
    yaml.dump(UserConfig, file);

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
    img = GrabImage(MirrorHwnd)
    return img
    
def CheckStatsRoutine():
    img = TakeMirrorImage(MirrorWindowHandle)
    crop = img.crop(box=StatsCropbox)
    statsImg = crop.resize((BarsWidth, BarsHeight))
    
    return ScanStats(statsImg)
     
def doConfig():
    print('HUD Configuration Initialized')
    
    
    if(MirrorWindowHandle != 0):        
        gameImage = GrabImage(MirrorWindowHandle)
        located = LocateImage(gameImage, "./health.png")
            
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
    
def setTibiaClient():
    wind = pyautogui.getActiveWindow()
    if wind:
        TibiaWindowHandle = wind._hWnd
        TibiaWindowTitle = wind.title
    else: 
        print('Could not find a window.')
        
def setMirrorWindow():
    wind = pyautogui.getActiveWindow()
    if wind:
        MirrorWindowHandle = wind._hWnd
        MirrorWindowTitle = wind.title
    else: 
        print('Could not find a window.')
        
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
    currentWindow = pyautogui.getActiveWindow()
    if(currentWindow):
        if(currentWindow._hWnd == targetHwnd):
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

while 1:
    try:
        if keyboard.is_pressed("ctrl+shift+1"):
            ScriptStatus = toggleBool(ScriptStatus)
            
        if keyboard.is_pressed("ctrl+shift+2"):
            doConfig()
            sleep(0.250)
            
        if keyboard.is_pressed("ctrl+shift+3"):
            ReloadUserPreferences()
            sleep(0.250)
            
            
        if(ScriptStatus):
            if isWinActive(TibiaWindowHandle):
                
                if ScriptDebugEnabled:
                    now = getNowMs()
                    print("Debug: Health and Mana Stats")
                    print(str(stats) + "\n")
                
                stats = CheckStatsRoutine()
                currentHealthPercent = stats[0]
                currentManaPercent = stats[1]
                
                if(not isExhausted(PotionExhaustTimer, PotionExhaustTime)):
                    if(currentHealthPercent < HealthPotionStage2Percent):
                        # Perform Action                    
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYDOWN, HealthPotionStage2Hotkey)
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYUP, HealthPotionStage2Hotkey)
                        
                        # Reset Timer
                        PotionExhaustTimer = getNowMs()
                        
                    elif(currentHealthPercent < HealthPotionStage1Percent):
                        # Perform Action                                       
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYDOWN, HealthPotionStage1Hotkey)
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYUP, HealthPotionStage1Hotkey)
                        
                        # Reset Timer
                        PotionExhaustTimer = getNowMs()
                    
                    elif(currentManaPercent < ManaPotionStage1Percent):
                        # Perform Action                    
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYDOWN, ManaPotionStage1Hotkey)
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYUP, ManaPotionStage1Hotkey)                
                                    
                        # Reset Timer
                        PotionExhaustTimer = getNowMs()
                
                if(not isExhausted(HealingSpellExhaustTimer, HealingSpellExhaustTime)):
                    if(currentHealthPercent < HealingSpellStage1Percent):
                        # Perform Action                                        
                        # keyboard.send(HealingSpellStage1Hotkey)
                        # keyboard.send(HealingSpellStage1Hotkey)
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYDOWN, HealingSpellStage1Hotkey)
                        win32api.PostMessage(TibiaWindowHandle, win32con.WM_KEYUP, HealingSpellStage1Hotkey)
                        
                        
                        # Reset Timer
                        HealingSpellExhaustTimer = getNowMs()

                if ScriptDebugEnabled:
                    diff = getNowMs() - now                
                    print("Debug: Status reading took ms: \n" + str(diff))        
            sleep(0.1)
    except KeyboardInterrupt:
        print("Saving User Preferences...")
        with open('preferences.yml', 'w') as file:
            yaml.dump(UserConfig, file);
        
        print("Exiting TibiaFlask...")
        sys.exit()
        
# keyboard.add_hotkey("ctrl+shift+4", doConfig)
# keyboard.add_hotkey("ctrl+shift+3", setMirrorWindow)
# keyboard.add_hotkey("ctrl+shift+2", setTibiaClient)
# keyboard.add_hotkey("ctrl+shift+1", toggleScript)    