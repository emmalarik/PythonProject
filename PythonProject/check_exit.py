from psychopy import event
from exit_procedure import exit_function


def check_for_escape():
    pressed_keys = event.getKeys(keyList=['escape'])
    if 'escape' in pressed_keys:
        exit_function()

    return False