from time import sleep
import keyboard

class InputManager:
  def SendKeystroke(key):
    if (InputManager.IsPressed("ctrl") or InputManager.IsPressed("alt") or InputManager.IsPressed("shift")):
      while (InputManager.IsPressed("ctrl") or InputManager.IsPressed("alt") or InputManager.IsPressed("shift")):
        sleep(0.01)
    keyboard.send(key)

  def IsPressed(key):
    return keyboard.is_pressed(key)
